"""Code adapted from https://github.com/mjablons1/nidaqmx-continuous-analog-io.
"""
import numpy as np

import nidaqmx as ni
from nidaqmx import stream_readers
import time

from sisyphy.process_logger import Process, Event
from sisyphy.barcode_synch.bcode_dataclasses import TimeStampData
from sisyphy.utils.custom_queue import SaturatingQueue
from sisyphy.barcode_synch.barcode_reading import find_single_barcode


class NiTimeStampProcess(Process):
    def __init__(self, *args, frame_duration, fs, frames_per_buffer, device_name, device_channel,
                 kill_event=None, debug_mode=False, **kwargs):
        self.kill_event = kill_event
        self.data_queue = SaturatingQueue()

        self.samples_per_frame = int(fs * frame_duration)
        # for some reason should be integer dividend of 10000
        if (10000 / self.samples_per_frame) % 1 != 0:
            raise ValueError("NI imposes that duration x framerate should be an integer dividend of 10000.")

        self.fs = fs
        self.frames_per_buffer = frames_per_buffer
        self.device_name = device_name
        self.device_channel = device_channel
        self.debug_mode =debug_mode

        # self.file = None
        super(NiTimeStampProcess, self).__init__(*args, **kwargs)

    def run(self):
        def _reading_task_callback(task_idx, event_type, num_samples, callback_data=None):
            """This callback is called every time a defined amount of samples has been acquired into the input buffer. This
            function is registered by register_every_n_samples_acquired_into_buffer_event and must follow prototype defined
            in nidaqxm documentation.
            Args:
                task_idx (int): Task handle index value
                event_type (nidaqmx.constants.EveryNSamplesEventType): ACQUIRED_INTO_BUFFER
                num_samples (int): Number of samples that were read into the read buffer.
                callback_data (object)[None]: User data can be additionally passed here, if needed.
            """
            reader.read_many_sample(read_buffer, num_samples, timeout=ni.constants.WAIT_INFINITELY)
            # # shift array:
            past_array[:self.samples_per_frame] = past_array[self.samples_per_frame:]
            past_array[self.samples_per_frame:] = read_buffer
            # print(len(past_array), sum(past_array > 2.5))
            tstamp_idx, tstamp_code = find_single_barcode(past_array, fs_khz=self.fs // 1000)

            # if we found a complete barcode:
            if tstamp_idx is not None:
                # send its time...
                now = time.time_ns()
                time_barcode_start_ns = now - np.int64((len(past_array) - tstamp_idx) / self.fs * 1e9)
                self.data_queue.put(TimeStampData(t_ns_buffer_stream=now,
                                                  t_ns_code=time_barcode_start_ns,
                                                  code=tstamp_code))
                if self.debug_mode:
                    print(time_barcode_start_ns, tstamp_code)
                # ...and clear the buffer to avoid double-counting
                past_array[:] = 0

            # The callback function must return 0 to prevent raising TypeError exception.
            return 0

        read_buffer = np.zeros((1, self.samples_per_frame), dtype=float)
        past_array = np.zeros(self.samples_per_frame * 2, dtype=float)

        with ni.Task() as ai_task:
            # We do not make this configurable as we assume a digital signal for this barcoding:
            ai_args = {'min_val': 0,
                       'max_val': 5,
                       'terminal_config': ni.constants.TerminalConfiguration.RSE}

            ai_task.ai_channels.add_ai_voltage_chan(self.device_name + self.device_channel, **ai_args)
            ai_task.timing.cfg_samp_clk_timing(rate=self.fs, sample_mode=ni.constants.AcquisitionType.CONTINUOUS)

            ai_task.input_buf_size = self.samples_per_frame * self.frames_per_buffer

            reader = stream_readers.AnalogMultiChannelReader(ai_task.in_stream)

            ai_task.register_every_n_samples_acquired_into_buffer_event(self.samples_per_frame, _reading_task_callback)
            ai_task.start()  # arms ai

            # loop until killed, here to remain always in the same NI context:
            while not self.kill_event.is_set():
                pass

            ai_task.stop()


if __name__ == "__main__":
    dev_name = 'Dev6'  # < remember to change to your device name, and channel input names below.
    ai0 = '/ai0'

    FS = 2000  # sample rate for input and output.
    # NOTE: Depending on your hardware sample clock frequency and available dividers some sample rates may not be supported.

    frames_per_buffer = 10  # nr of frames fitting into the buffer of each measurement channel.
    # NOTE  With my NI6211 it was necessary to override the default buffer size to prevent under/over run at high sample
    # rates.
    dur = 1.25  # duration in seconds of reading window

    from time import sleep
    # from sisyphy.sphere_velocity.processes import EstimateVelocityProcess
    kill_evt = Event()

    # p_mouse = EstimateVelocityProcess(kill_event=kill_evt)
    p_tstamp = NiTimeStampProcess(kill_event=kill_evt, frame_duration=dur, fs=FS, frames_per_buffer=frames_per_buffer,
                                  device_name=dev_name, device_channel=ai0, debug_mode=True)
    # p_receiver = ReceivingProcess(kill_event=kill_evt,
    #                               mouse_queue=p_mouse.data_queue,
    #                               tstamp_queue=p_tstamp.data_queue)

    p_tstamp.start()
    sleep(20)
    kill_evt.set()
    sleep(0.5)
    p_tstamp.join()