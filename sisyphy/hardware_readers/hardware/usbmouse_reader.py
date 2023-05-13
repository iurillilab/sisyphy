import abc
from dataclasses import dataclass
from time import time_ns
from typing import Tuple

import numpy as np
import usb1

from sisyphy.utils.dataclasses import TimestampedDataClass


@dataclass
class MouseVelocityData(TimestampedDataClass):
    """Timestamped values for mouse motion over the two coordinates."""

    x: int
    y: int


class AbstractMouse(metaclass=abc.ABCMeta):
    """Base interface for reading movement velocity from a mouse.

    Public methods
    --------------

        self.read_velocity:
            returns a MouseVelocity data class with x and y velocities.

    Private methods
    ---------------
        _read_velocity:
            Method to implement in subclasses for reading the actual data from the mouse.

        _initialise_mouse:
            Method to implement in subclasses for initializing the mouse.

    """

    def __init__(self):

        self.mouse = None
        self._initialise_mouse()

    @abc.abstractmethod
    def _initialise_mouse(self) -> None:
        pass

    @abc.abstractmethod
    def _read_velocities(self) -> Tuple[float, float]:
        """Empty method to velocities from hardware."""
        pass

    def get_velocities(self) -> MouseVelocityData:
        """Public method to read mouse velocity"""
        x, y = self._read_velocities()
        return MouseVelocityData(x=x, y=y)


class MockMouse(AbstractMouse):
    """Interface to a fake mouse for testing purposes.
    Implements the _read_velocities method to give random data."""

    TIMESTEP_NS = 50000000  # timestep between emitted velocities

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.starting_t = time_ns()
        self.phase_x = np.random.randn()
        self.phase_y = np.random.randn()
        self.prev_elapsed = 0

    def _initialise_mouse(self) -> None:
        pass

    def _read_mouse(self) -> None:
        pass

    def _read_velocities(self) -> Tuple[float, float]:
        elapsed = 0
        while elapsed - self.prev_elapsed < self.TIMESTEP_NS:
            elapsed = time_ns() - self.starting_t
        self.prev_elapsed = elapsed
        return np.random.randint(-127, 127), np.random.randint(-127, 127)


class WinUsbMouse(AbstractMouse):
    """Interface to a mouse configured using the WinUSB drivers.
    Implements the _read_velocities method to read data from the real mouse.
    """

    def __init__(self, ind=0, ig_id_vendor=0x046D, ig_id_product=0xC08B):
        """
        Parameters
        ----------
        ind : int
            Index of the device (in case there's multiple ones)
        iGIdVendor : hex
            Vendor ID of the mouse (default for Logitech)
        iGIdProduct : hex
            Product ID of the mouse (default for G502)
        """
        self.ind = ind
        self.ig_id_vendor = ig_id_vendor
        self.ig_id_product = ig_id_product
        super().__init__()

    def _initialise_mouse(self) -> None:
        # Find our device:
        ctx = usb1.LibUSBContext()
        usb_devices = ctx.getDeviceList()
        matching_devices = [
            dev
            for dev in usb_devices
            if dev.getVendorID() == self.ig_id_vendor
            and dev.getProductID() == self.ig_id_product
        ]

        # Open device:
        self.mouse = matching_devices[self.ind].open()
        self.mouse.claimInterface(0)

    @staticmethod
    def _unsigned2signed(u, d):
        """Convert 2 unsigned char to a signed int."""

        if d < 127:
            return float(d * 256 + u)
        else:
            return float((d - 255) * 256 - 256 + u)

    def _read_velocities(self) -> Tuple[float, float]:
        """Read instantaneous velocity from a mouse.

        Returns
        -------
        tuple

        """
        x, y = 0, 0
        TIMEOUT = 1  # This does not seem to change anything as long as it is > 1, so we don't make it configurable.
        try:
            readout = [dat for dat in self.mouse.interruptRead(0x81, 8, TIMEOUT)]
            y = self._unsigned2signed(readout[2], readout[3])
            x = self._unsigned2signed(readout[4], readout[5])
        except usb1.USBErrorTimeout:
            pass

        return x, y


if __name__ == "__main__":
    from datetime import datetime

    mouse0, mouse1 = WinUsbMouse(ind=0), WinUsbMouse(ind=1)

    COUNTER = 1000
    pos_arr = np.empty((5, COUNTER))
    t0 = datetime.now()
    for i in range(COUNTER):
        if i % 100 == 0:
            print(i)
        vels = mouse1.get_velocities()
        x0, y0 = vels.x, vels.y
        vels = mouse1.get_velocities()
        x1, y1 = vels.x, vels.y
        pos_arr[:, i] = (x0, x1, y0, y1, (datetime.now() - t0).total_seconds())
        t0 = datetime.now()
    pos_arr[4, :] = np.cumsum(pos_arr[4, :])

    np.save(r"C:\Users\SNeurobiology\Documents\Luigi\vr-test\mousetest2.npy", pos_arr)
