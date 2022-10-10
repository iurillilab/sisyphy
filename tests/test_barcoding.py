import numpy as np
from sisyphy.barcode_synch.timestamping_process import NiTimeStampProcess
from multiprocessing import Event


# TODO mark this as hardware specific!
def test_barcoding_process():
    dev_name = "Dev6"  # < remember to change to your device name, and channel input names below.
    ai0 = "/ai0"

    fs = 2000
    frames_per_buffer = 10
    dur = 1.25

    from time import sleep

    kill_evt = Event()

    p_tstamp = NiTimeStampProcess(
        kill_event=kill_evt,
        frame_duration=dur,
        fs=fs,
        frames_per_buffer=frames_per_buffer,
        device_name=dev_name,
        device_channel=ai0,
        debug_mode=True,
    )

    p_tstamp.start()
    sleep(5)
    timestamps = p_tstamp.data_queue.get_all()
    kill_evt.set()

    assert len(timestamps) == 1
    assert type(timestamps[0].code) == np.int64
    sleep(0.5)
    p_tstamp.join()