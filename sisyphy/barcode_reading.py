"""Code adapted from https://github.com/mjablons1/nidaqmx-continuous-analog-io.
"""
import pyqtgraph as pg
import numpy as np

import nidaqmx as ni
from nidaqmx import stream_readers
import time
from pathlib import Path
from sisyphy.process_logger import LoggingProcess, TerminableProcess, Process, Event
from datetime import datetime


def _find_barcode(barcode_array):
    """Find complete barcode in array of voltage reads. The barcode has to be completely
    in the array - an half read barcode will not be detected. Make sure your sampling capture
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


dev_name = 'Dev1'  # < remember to change to your device name, and channel input names below.
ai0 = '/ai0'

FS = 2000  # sample rate for input and output.
# NOTE: Depending on your hardware sample clock frequency and available dividers some sample rates may not be supported.

frames_per_buffer = 100  # nr of frames fitting into the buffer of each measurement channel.
# NOTE  With my NI6211 it was necessary to override the default buffer size to prevent under/over run at high sample
# rates.
refresh_rate_hz = 1
samples_per_frame = int(FS // refresh_rate_hz)

dur = 15  # duration in seconds
samples_total = dur * FS
acquisition_buffer = np.zeros(samples_total, dtype=float)
timebase = np.arange(samples_per_frame) / FS


class NiTimeStampProcess(Process):
    def __init__(self, *args, **kwargs):
        self.kill_event = Event()
        self.root = Path(r"C:\Users\SNeurobiology\Documents\Luigi\vr-test\barcode_acq")
        self.filename = self.root / datetime.now().strftime("%Y%m%d_%H.%M.%S_timestamps.txt")
        self.file = None
        super(NiTimeStampProcess, self).__init__(*args, **kwargs)


    def _write_entry(self, timestamp, message):
        if self.file is None:
            self.file = open(self.filename, "w")
        self.file.write(
            f"{timestamp},{message}\n"
        )

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
            if tstamp_idx is not None:
                time_barcode_start_ns = time.time_ns() - (len(past_array) - tstamp_idx) / FS * 10e9
                print(time_barcode_start_ns)
                self._write_entry(time_barcode_start_ns, tstamp_code)


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


if __name__ == "__main__":
    from time import sleep
    p = NiTimeStampProcess()
    p.start()
    sleep(10)
    p.kill_event.set()
    sleep(0.5)
    p.join()