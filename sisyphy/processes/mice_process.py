from multiprocessing import Event, Process

import numpy as np
import time

from sisyphy.custom_dataclasses import (
    EstimatedVelocityData,
    RawMiceVelocityData,
)
from sisyphy.defaults import BALL_CALIBRATION
from sisyphy.hardware.usbmouse import WinUsbMouse, MouseVelocityData
from sisyphy.custom_queue import SaturatingQueue

# Streaming dataclasses between processes does impact performance a bit, but hopefully not to a meaningful degree
# (18 us vs 14 us / it for something with 2 integers and a timestamp, vs an equivalent tuple)


class _BaseMouseProcess(Process):
    def __init__(self, kill_event):
        """Process
        Parameters
        ----------
        kill_event
        ouput
        """
        super().__init__()
        self.data_queue = SaturatingQueue()
        self.mouse0, self.mouse1 = None, None
        self.kill_event = kill_event

    def _setup_mice(self) -> None:
        self.mouse0 = WinUsbMouse(ind=0)
        # self.mouse1 = Mouse(ind=1)

    def _read_mice(self) -> RawMiceVelocityData:
        return RawMiceVelocityData(
            mouse0=self.mouse0.get_velocities(), mouse1=MouseVelocityData(x=0, y=0),#self.mouse1.read_velocity()
        )

    def _get_message(self):
        """Defined in subclasses, changes depending on whether we're streaming raw data or processed data."""
        pass

    def run(self):
        self._setup_mice()
        while not self.kill_event.is_set():
            # We put values in the queue only for non-zero reading, useless to clog otherwise
            # if any(v != 0 for v in mouse0_vel + mouse1_vel):
            msg = self._get_message()
            #print(msg, time.time_ns())
            # We stream dataclasses as this seems to impact only 10% speed vs tuples.

            self.data_queue.put(msg)


class RawMiceProcess(_BaseMouseProcess):
    """Subclass that streams raw mouse coordinates."""

    def _get_message(self):
        """Stream raw data."""
        return self._read_mice()


class EstimateVelocityProcess(_BaseMouseProcess):
    """Subclass that streams raw mouse coordinates."""

    @staticmethod
    def _trasform_coords(array: np.array) -> np.array:
        return BALL_CALIBRATION @ array

    def _get_message(self):
        """Stream raw data."""
        mice_data = self._read_mice()

        # sequence for transformation is M0_x, M0_y, M1_x, M1_y
        arr = np.array(
            [
                mice_data.mouse0.x,
                mice_data.mouse0.y,
                mice_data.mouse1.x,
                mice_data.mouse1.y,
            ]
        )
        # Arbitrary threshold for funny values:
        # arr[np.abs(arr) > 500] = 0
        trasformed = self._trasform_coords(arr)

        return EstimatedVelocityData(
            pitch=trasformed[0], yaw=trasformed[1], roll=-trasformed[2]
        )


#
# class ReadProcess(Process):
#     def __init__(self, *args, data_queue: SaturatingQueue, kill_event: Event, **kwargs):
#         self.kill_event = kill_event
#         self.data_queue = data_queue
#         self.accumulator = QueueDataAccumulator(data_queue=data_queue)
#         super(ReadProcess, self).__init__(*args, **kwargs)
#
#     def run(self) -> None:
#         while not self.kill_event.is_set():
#             self.accumulator.update_list()
#         print("here", len(self.accumulator.stored_data))
