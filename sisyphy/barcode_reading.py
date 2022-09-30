"""Code adapted from https://github.com/mjablons1/nidaqmx-continuous-analog-io.
"""
import numpy as np

import nidaqmx as ni
from nidaqmx import stream_readers
import time
from pathlib import Path
from sisyphy.process_logger import Process, Event
from datetime import datetime
from sisyphy.custom_dataclasses import TimeStampData
from sisyphy.custom_queue import SaturatingQueue
import pandas as pd


def _find_barcode(barcode_array):
    """Find complete barcode in array of voltage reads. The barcode has to be completely
    in the array - a half read barcode will not be detected. Make sure your sampling capture
    all elements of the barcode in the array passed here, and no more than one barcode.
    This code runs at 50us on a 8k sample, so should not affect timing too much.
    """
    DURATION_THR = 15  # duration in ms below which one pulse is considered a wrapper
    BIT_WIDTH_MS = 30  # duration of each bit in ms
    WRAPPER_WIDTH_MS = 10  # duration of the wrapper in ms
    SIG_THR = 2.5  # threshold on signal for ON
    DIFF_THR = 0.5  # threshold on diff for transition
    FS_KHZ = 2
    N_BITS = 32

    wrap_width_pts = WRAPPER_WIDTH_MS * FS_KHZ
    bit_width_pts = BIT_WIDTH_MS * FS_KHZ
    duration_thr_pts = DURATION_THR * FS_KHZ

    bit_base = 2**np.arange(N_BITS, dtype=np.int64)

    pulses_diff = np.diff(barcode_array)
    event_indexes = np.argwhere(np.abs(pulses_diff) > DIFF_THR)[:, 0]

    # Get on and off events:
    on_events = pulses_diff[event_indexes] > DIFF_THR
    off_events =  ~on_events

    # Find wrappers by checking for off-on-off transitions faster than DURATION_THR ms:
    wrapper_select = on_events[:-1] & off_events[1:] & (np.diff(event_indexes) < duration_thr_pts)

    # Make sure we have here the entirety of the barcode
    if (sum(wrapper_select) < 2) or (sum(wrapper_select) > 2):
        return None, None

    wrapper_indexes = event_indexes[:-1][wrapper_select]

    # start reading from middle of first barcode bin:
    reading_start = wrapper_indexes[0] + wrap_width_pts * 2 +  bit_width_pts // 2

    # Read voltage level in the middle of the bins (#TODO maybe an average would be better):
    bit_center_indexes = reading_start + np.arange(N_BITS) * bit_width_pts
    bool_bits = (barcode_array[bit_center_indexes] > SIG_THR)

    # Convert sequence to binary number and return with index:
    return wrapper_indexes[0], sum(bit_base * (barcode_array[bit_center_indexes] > SIG_THR))


dev_name = 'Dev3'  # < remember to change to your device name, and channel input names below.
ai0 = '/ai0'

FS = 2000  # sample rate for input and output.
# NOTE: Depending on your hardware sample clock frequency and available dividers some sample rates may not be supported.

frames_per_buffer = 10  # nr of frames fitting into the buffer of each measurement channel.
# NOTE  With my NI6211 it was necessary to override the default buffer size to prevent under/over run at high sample
# rates.
dur = 1.25  # duration in seconds of reading window
samples_per_frame = int(FS * dur)  # for some reason should be integer dividend of 10000


class NiTimeStampProcess(Process):
    def __init__(self, *args, kill_event=None, **kwargs):
        self.kill_event = kill_event
        self.data_queue = SaturatingQueue()

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
            past_array[:samples_per_frame] = past_array[samples_per_frame:]
            past_array[samples_per_frame:] = read_buffer
            tstamp_idx, tstamp_code = _find_barcode(past_array)

            # if we found a complete barcode, send its time and clear the buffer to avoid double-counting:
            if tstamp_idx is not None:
                now = time.time_ns()
                time_barcode_start_ns = now - np.int64((len(past_array) - tstamp_idx) / FS * 1e9)
                self.data_queue.put(TimeStampData(t_ns_buffer_stream=now,
                                                  t_ns_code=time_barcode_start_ns,
                                                  code=tstamp_code))
                past_array[:] = 0

            # The callback function must return 0 to prevent raising TypeError exception.
            return 0

        read_buffer = np.zeros((1, samples_per_frame), dtype=float)
        past_array = np.zeros(samples_per_frame * 2, dtype=float)

        with ni.Task() as ai_task:

            ai_args = {'min_val': 0,
                       'max_val': 5,
                       'terminal_config': ni.constants.TerminalConfiguration.RSE}

            ai_task.ai_channels.add_ai_voltage_chan(dev_name + ai0, **ai_args)
            ai_task.timing.cfg_samp_clk_timing(rate=FS, sample_mode=ni.constants.AcquisitionType.CONTINUOUS)

            ai_task.input_buf_size = samples_per_frame * frames_per_buffer

            reader = stream_readers.AnalogMultiChannelReader(ai_task.in_stream)

            ai_task.register_every_n_samples_acquired_into_buffer_event(samples_per_frame, _reading_task_callback)
            ai_task.start()  # arms ai but does not trigger
            while not self.kill_event.is_set():
                pass

            ai_task.stop()


class ReceivingProcess(Process):
    def __init__(self, *args, mouse_queue=None, tstamp_queue=None, kill_event=None, **kwargs):
        self.mouse_queue = mouse_queue
        self.tstamp_queue = tstamp_queue
        self.kill_event = kill_event

        self.root = Path(r"C:\Users\SNeurobiology\data\luigi-testing\barcode_testing")
        self.timestamp = datetime.now().strftime("%Y%m%d_%H.%M.%S")

        super(ReceivingProcess, self).__init__(*args, **kwargs)

    def run(self) -> None:
        mouse = []
        p_tstamp = []
        while not self.kill_event.is_set():
            m = self.mouse_queue.get_all()
            mouse.extend(m)

            p_tstamp.extend(self.tstamp_queue.get_all())

        pd.DataFrame(mouse).to_csv(self.root / (self.timestamp + "_mouse.txt"))
        pd.DataFrame(p_tstamp).to_csv(self.root / (self.timestamp + "_timestamps.txt"))


if __name__ == "__main__":
    from time import sleep
    from sisyphy.hardware.mice_process import EstimateVelocityProcess
    kill_evt = Event()

    p_mouse = EstimateVelocityProcess(kill_event=kill_evt)
    p_tstamp = NiTimeStampProcess(kill_event=kill_evt)
    p_receiver = ReceivingProcess(kill_event=kill_evt,
                                  mouse_queue=p_mouse.data_queue,
                                  tstamp_queue=p_tstamp.data_queue)

    for p in [p_tstamp, p_mouse, p_receiver]:
        p.start()
    sleep(3600)
    kill_evt.set()
    sleep(0.5)
    for p in [p_tstamp, p_mouse, p_receiver]:
        p.join()