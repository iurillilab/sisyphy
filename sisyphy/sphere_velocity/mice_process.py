from multiprocessing import Process

import numpy as np

from sisyphy.sphere_velocity.defaults import BALL_CALIBRATION
from sisyphy.sphere_velocity.hardware.usbmouse import (
    DummyMouse,
    MouseVelocityData,
    WinUsbMouse,
)
from sisyphy.sphere_velocity.sphere_dataclasses import (
    EstimatedVelocityData,
    RawMiceVelocityData,
)
from sisyphy.utils.custom_queue import SaturatingQueue

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
        pass

    def _read_mice(self) -> RawMiceVelocityData:
        return RawMiceVelocityData(
            mouse0=self.mouse0.get_velocities(), mouse1=self.mouse1.get_velocities()
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
            # print(msg, time.time_ns())
            # We stream dataclasses as this seems to impact only 10% speed vs tuples.

            self.data_queue.put(msg)

        # clear queue before closing:
        d = self.data_queue.get_all()
        print(f"Closing mice, cleared {len(d)} elements from queue")


class RawUsbMiceProcess(_BaseMouseProcess):
    """Subclass that streams raw mouse coordinates."""

    def _get_message(self):
        """Stream raw data."""
        return self._read_mice()

    def _setup_mice(self) -> None:
        self.mouse0 = WinUsbMouse(ind=0)
        self.mouse1 = WinUsbMouse(ind=1)


class SphereVelocityProcess(RawUsbMiceProcess):
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


class DummyVelocityProcess(SphereVelocityProcess):
    """Subclass that simulate data stream from fake mouse."""

    def _setup_mice(self) -> None:
        self.mouse0 = DummyMouse()
        self.mouse1 = DummyMouse()


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
