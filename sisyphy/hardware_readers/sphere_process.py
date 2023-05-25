import abc
from dataclasses import dataclass
from multiprocessing import Process

import numpy as np

from sisyphy.hardware_readers.defaults import BALL_CALIBRATION
from sisyphy.hardware_readers.hardware.usbmouse_reader import (
    MockMouse,
    MouseVelocityData,
    WinUsbMouse,
)
from sisyphy.utils.custom_queue import SaturatingQueue
from sisyphy.utils.dataclasses import TimestampedDataClass


# Note on dataclass usage:
# Streaming dataclasses between processes does impact performance a bit, but hopefully not to a meaningful degree
# (18 us vs 14 us / it for something with 2 integers and a timestamp, vs an equivalent tuple)
@dataclass
class RawMiceData:
    """Dataclass to keep together velocity data from two mice."""

    mouse0: MouseVelocityData
    mouse1: MouseVelocityData


@dataclass
class RawVelSphereData(TimestampedDataClass):
    """Dataclass to keep together velocity data from two mice."""

    x0: int
    y0: int
    x1: int
    y1: int


@dataclass
class EstimatedVelSphereData(TimestampedDataClass):
    """Estimated yaw, pitch and roll from the data from two mice."""

    pitch: float
    roll: float
    yaw: float
    x0: int
    y0: int
    x1: int
    y1: int


class SphereReaderProcess(Process, metaclass=abc.ABCMeta):
    """Abstract class to interface with a sphere that is read by two mice, and its velocities are streamed."""

    def __init__(self, kill_event):
        """
        Parameters
        ----------
        kill_event : Event object
            Event to set for termination of the streaming process.

        """
        super().__init__()
        self.data_queue = SaturatingQueue()
        self.mouse0, self.mouse1 = None, None
        self.kill_event = kill_event

    @abc.abstractmethod
    def _setup_mice(self) -> None:
        pass

    def _read_mice(self) -> RawMiceData:
        return RawMiceData(
            mouse0=self.mouse0.get_velocities(), mouse1=self.mouse1.get_velocities()
        )

    @abc.abstractmethod
    def _get_message(self):
        """Defined in subclasses, changes depending on whether we're streaming raw data or processed data."""
        pass

    def run(self):
        self._setup_mice()
        while not self.kill_event.is_set():
            msg = self._get_message()
            self.data_queue.put(msg)

        # clear queue before closing:
        d = self.data_queue.get_all()
        print(f"Closing mice, cleared {len(d)} elements from queue")


class MockSphereReaderProcess(SphereReaderProcess):
    """Subclass that simulate data stream from fake mice."""

    def _setup_mice(self) -> None:
        self.mouse0 = MockMouse()
        self.mouse1 = MockMouse()

    def _get_message(self):
        mice_data = self._read_mice()

        return RawVelSphereData(
            x0=mice_data.mouse0.x,
            y0=mice_data.mouse0.y,
            x1=mice_data.mouse1.x,
            y1=mice_data.mouse1.y,
        )


class UsbSphereReaderProcess(SphereReaderProcess, metaclass=abc.ABCMeta):
    """A - still abstract - class to read sphere velocity with WinUSB mice."""

    def _setup_mice(self) -> None:
        # print("Setting up mice")
        self.mouse0 = WinUsbMouse(ind=0)
        self.mouse1 = WinUsbMouse(ind=1)


class RawUsbSphereReaderProcess(UsbSphereReaderProcess):
    """Read raw data from the mice of a USB Sphere."""

    # def _get_message(self):
    #    return self._read_mice()


class CalibratedSphereReaderProcess(UsbSphereReaderProcess):
    """Estimate spherical velocities from the data of two mice and stream those together with
    the raw data."""

    @staticmethod
    def _trasform_coords(array: np.array) -> np.array:
        """Compute dot product with calibrated matrix."""
        return BALL_CALIBRATION @ array

    def _get_message(self):
        mice_data = self._read_mice()
         # print(mice_data)
        # sequence for transformation is M0_x, M0_y, M1_x, M1_y:
        arr = np.array(
            [
                mice_data.mouse0.x,
                mice_data.mouse0.y,
                mice_data.mouse1.x,
                mice_data.mouse1.y,
            ]
        )

        transformed = self._trasform_coords(arr)

        return EstimatedVelSphereData(
            pitch=transformed[0],
            yaw=transformed[1],
            roll=-transformed[2],
            x0=mice_data.mouse0.x,
            y0=mice_data.mouse0.y,
            x1=mice_data.mouse1.x,
            y1=mice_data.mouse1.y,
        )
