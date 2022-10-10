"""Code adapted from https://github.com/mjablons1/nidaqmx-continuous-analog-io.
"""
import numpy as np


def find_single_barcode(barcode_array, fs_hz):
    """Find complete barcode in array of voltage reads. The barcode has to be completely
    in the array - a half read barcode will not be detected. Make sure your sampling capture
    all elements of the barcode in the array passed here, and no more than one barcode.
    This code runs at 50us on a 8k sample, so should not affect timing too much.
    """
    DURATION_THR_S = (
        0.015  # duration in s below which one pulse is considered a wrapper
    )
    BIT_WIDTH_S = 0.030  # duration of each bit in s
    WRAPPER_WIDTH_S = 0.010  # duration of the wrapper in s
    SIG_THR = 2.5  # threshold on signal for ON
    DIFF_THR = 0.5  # threshold on diff for transition
    N_BITS = 32

    wrap_width_pts = int(WRAPPER_WIDTH_S * fs_hz)
    bit_width_pts = int(BIT_WIDTH_S * fs_hz)
    duration_thr_pts = int(DURATION_THR_S * fs_hz)

    bit_base = 2 ** np.arange(N_BITS, dtype=np.int64)

    pulses_diff = np.diff(barcode_array)
    event_indexes = np.argwhere(np.abs(pulses_diff) > DIFF_THR)[:, 0]

    # If there's no events, or the first transition is up, just return:
    if len(event_indexes) == 0 or pulses_diff[event_indexes[0]] < 0:
        return None, None
    # Get on and off events:
    on_events = pulses_diff[event_indexes] > DIFF_THR
    off_events = ~on_events

    # Find wrappers by checking for off-on-off transitions faster than DURATION_THR ms:
    wrapper_select = (
        on_events[:-1] & off_events[1:] & (np.diff(event_indexes) < duration_thr_pts)
    )

    # Make sure we have here the entirety of the barcode
    if sum(wrapper_select) != 2:
        return None, None

    wrapper_indexes = event_indexes[:-1][wrapper_select]

    # start reading from middle of first barcode bin:
    reading_start = wrapper_indexes[0] + wrap_width_pts * 2 + bit_width_pts // 2

    # Read voltage level in the middle of the bins (#TODO maybe an average would be better):
    bit_center_indexes = reading_start + np.arange(N_BITS) * bit_width_pts

    bool_bits = barcode_array[bit_center_indexes] > SIG_THR

    # Convert sequence to binary number and return with index:
    return wrapper_indexes[0], sum(bit_base * bool_bits)
