"""Code adapted from https://github.com/mjablons1/nidaqmx-continuous-analog-io.
"""
import time

import nidaqmx as ni
import numpy as np
from nidaqmx import stream_readers

from sisyphy.barcode_synch.barcode_reading import find_single_barcode
from sisyphy.barcode_synch.bcode_dataclasses import TimeStampData
from multiprocessing import Event, Process
from sisyphy.utils.custom_queue import SaturatingQueue


# TODO maybe in this class hardware and barcode reading logic might be separated better.
# I will change this if it happens that I will be reading the signal with something different from an NI.


class NiTimeStampProcess(Process):
    def __init__(
        self,
        *args,
        frame_duration: float,
        fs: int,
        frames_per_buffer: int,
        device_name: str,
        device_channel: str,
        kill_event: Event = None,
        debug_mode=False,
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        frame_duration : float
            Duration of a reading frame, in seconds. Should be longer than a barcode, but shorter than their period!
        fs : int
            Sampling rate of the board, in seconds. Recommended > 10 samples for the shorter barcode up time.
        frames_per_buffer : int
            Number of reading frames in the board buffer. Not sure about the effects. 10 works with NI USB6008.
        device_name : str
            name of NI device.
        device_channel : str
            channel of NI device.
        kill_event : Event
            event to kill the process.
        debug_mode
        kwargs
        """
        self.kill_event = kill_event
        self.data_queue = SaturatingQueue()

        self.samples_per_frame = int(fs * frame_duration)
        # for some reason should be integer dividend of 10000
        if (10000 / self.samples_per_frame) % 1 != 0:
            raise ValueError(
                "NI imposes that duration x framerate should be an integer dividend of 10000."
            )

        self.fs = fs
        self.frames_per_buffer = frames_per_buffer
        self.device_name = device_name
        self.device_channel = device_channel
        self.debug_mode = debug_mode

        # self.file = None
        super(NiTimeStampProcess, self).__init__(*args, **kwargs)

    def run(self):
        def _reading_task_callback(
            task_idx, event_type, num_samples, callback_data=None
        ):
            """This callback is called every time a defined amount of samples has been acquired.
            Thisfunction must follow prototype defined in nidaqxm documentation.
            Args:
                ...
                num_samples (int): Number of samples that were read into the read buffer.
                ...
            """
            reader.read_many_sample(
                read_buffer, num_samples, timeout=ni.constants.WAIT_INFINITELY
            )
            # # shift array:
            past_array[: self.samples_per_frame] = past_array[self.samples_per_frame :]
            past_array[self.samples_per_frame :] = read_buffer
            # print(len(past_array), sum(past_array > 2.5))
            tstamp_idx, tstamp_code = find_single_barcode(past_array, self.fs)

            # if we found a complete barcode:
            if tstamp_idx is not None:
                # send its time...
                now = time.time_ns()
                barcode_frame_time_s = (len(past_array) - tstamp_idx) / self.fs
                time_barcode_start_ns = now - np.int64(barcode_frame_time_s * 1e9)
                self.data_queue.put(
                    TimeStampData(
                        t_ns_buffer_stream=now,
                        t_ns_code=time_barcode_start_ns,
                        code=tstamp_code,
                    )
                )
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
            ai_args = {
                "min_val": 0,
                "max_val": 5,
                "terminal_config": ni.constants.TerminalConfiguration.RSE,
            }

            ai_task.ai_channels.add_ai_voltage_chan(
                self.device_name + self.device_channel, **ai_args
            )
            ai_task.timing.cfg_samp_clk_timing(
                rate=self.fs, sample_mode=ni.constants.AcquisitionType.CONTINUOUS
            )

            ai_task.input_buf_size = self.samples_per_frame * self.frames_per_buffer

            reader = stream_readers.AnalogMultiChannelReader(ai_task.in_stream)

            ai_task.register_every_n_samples_acquired_into_buffer_event(
                self.samples_per_frame, _reading_task_callback
            )
            ai_task.start()  # arms ai

            # loop until killed, put here to remain always in the same NI context:
            while not self.kill_event.is_set():
                pass

            ai_task.stop()


if __name__ == "__main__":
    dev_name = "Dev6"  # < remember to change to your device name, and channel input names below.
    ai0 = "/ai0"

    FS = 2000
    frames_per_buffer = 10
    dur = 1.25

    from time import sleep

    kill_evt = Event()

    p_tstamp = NiTimeStampProcess(
        kill_event=kill_evt,
        frame_duration=dur,
        fs=FS,
        frames_per_buffer=frames_per_buffer,
        device_name=dev_name,
        device_channel=ai0,
        debug_mode=True,
    )

    p_tstamp.start()
    sleep(10)
    kill_evt.set()
    sleep(0.5)
    p_tstamp.join()
