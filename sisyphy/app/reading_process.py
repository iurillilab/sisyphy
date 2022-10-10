from datetime import datetime
from multiprocessing import Process
from pathlib import Path

import pandas as pd


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
    dev_name = 'Dev3'  # < remember to change to your device name, and channel input names below.
    ai0 = '/ai0'

    FS = 2000  # sample rate for input and output.
    # NOTE: Depending on your hardware sample clock frequency and available dividers some sample rates may not be supported.

    frames_per_buffer = 10  # nr of frames fitting into the buffer of each measurement channel.
    # NOTE  With my NI6211 it was necessary to override the default buffer size to prevent under/over run at high sample
    # rates.
    dur = 1.25  # duration in seconds of reading window
    samples_per_frame = int(FS * dur)  # for some reason should be integer dividend of 10000

    from time import sleep
    # from sisyphy.sphere_velocity.processes import EstimateVelocityProcess
    kill_evt = Event()

    # p_mouse = EstimateVelocityProcess(kill_event=kill_evt)
    p_tstamp = NiTimeStampProcess(kill_event=kill_evt)
    # p_receiver = ReceivingProcess(kill_event=kill_evt,
    #                               mouse_queue=p_mouse.data_queue,
    #                               tstamp_queue=p_tstamp.data_queue)

    for p in [p_tstamp, p_mouse, p_receiver]:
        p.start()
    sleep(3600)
    kill_evt.set()
    sleep(0.5)
    for p in [p_tstamp, p_mouse, p_receiver]:
        p.join()