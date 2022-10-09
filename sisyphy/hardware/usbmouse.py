from typing import Tuple
import numpy as np
import usb1

from sisyphy.custom_dataclasses import MouseVelocityData


def _u2s(u, d):
    """Convert 2 unsigned char to a signed int.
    """

    if d < 127:
        return float(d * 256 + u)
    else:
        return float((d - 255) * 256 - 256 + u)


class Mouse:
    def __init__(self):
        """Base class for reading velocity from a mouse.
        """
        self.mouse = None
        self._initialise_mouse()

    def _initialise_mouse(self) -> None:
        pass

    def _read_velocities(self) -> Tuple[float, float]:
        """Empty method to velocities from hardware.
        """
        pass

    def get_velocities(self) -> MouseVelocityData:
        """Public method to read mouse velocity"""
        x, y = self._read_velocities()
        return MouseVelocityData(x=x, y=y)


class DummyMouse(Mouse):
    def _read_velocities(self) -> Tuple[float, float]:
        return np.random.randn(), np.random.randn()


class WinUsbMouse(Mouse):
    def __init__(self, ind=0, ig_id_vendor=0x046D, ig_id_product=0xC08B):
        """Minimal class to instantiate and read from a mouse configured using the WinUSB drivers.

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

    def _initialise_mouse(self):
        # Find our device:
        ctx = usb1.LibUSBContext()
        usb_devices = ctx.getDeviceList()
        matching_devices = [
            dev
            for dev in usb_devices
            if dev.getVendorID() == self.ig_id_vendor and dev.getProductID() == self.ig_id_product
        ]

        # Open device:
        self.mouse = matching_devices[self.ind].open()
        self.mouse.claimInterface(0)

    def _read_velocities(self):
        """Read instantaneous velocity from a mouse. No timeout argument to pass as it does not seem to do anything.

        Returns
        -------
        tuple

        """
        x, y = 0, 0
        TIMEOUT = 1  # This does not seem to change anything as long as it is > 1, so we don't make it configurable.
        try:
            readout = [dat for dat in self.mouse.interruptRead(0x81, 8, TIMEOUT)]
            y = _u2s(readout[2], readout[3])
            x = _u2s(readout[4], readout[5])
        except usb1.USBErrorTimeout:
            pass

        return x, y


if __name__ == "__main__":
    from datetime import datetime

    mouse0, mouse1 = WinUsbMouse(ind=0), WinUsbMouse(ind=1)

    COUNTER = 10000
    pos_arr = np.empty((5, COUNTER))
    t0 = datetime.now()
    for i in range(COUNTER):
        if i % 100 == 0:
            print(i)
        x0, y0 = mouse1.get_velocities()
        x1, y1 = mouse1.get_velocities()
        pos_arr[:, i] = (x0, x1, y0, y1, (datetime.now() - t0).total_seconds())
        t0 = datetime.now()
    pos_arr[4, :] = np.cumsum(pos_arr[4, :])

    np.save(r"C:\Users\SNeurobiology\Documents\Luigi\vr-test\mousetest2.npy", pos_arr)
