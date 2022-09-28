import numpy as np
import usb1

from sisyphy.custom_dataclasses import MouseVelocityData


def _u2s(u, d):
    """Convert 2 unsigned char to a signed int"""
    if d < 127:
        return d * 256 + u
    else:
        return (d - 255) * 256 - 256 + u


class Mouse:
    def __init__(self, ind=0, iGIdVendor=0x046D, iGIdProduct=0xC08B):
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

        # Find our device:
        ctx = usb1.LibUSBContext()
        alldevs = ctx.getDeviceList()
        devs = [
            dev
            for dev in alldevs
            if dev.getVendorID() == iGIdVendor and dev.getProductID() == iGIdProduct
        ]

        # Open device:
        self.dev = devs[ind].open()
        self.dev.claimInterface(0)

    def read_velocity(self):
        """Read instantaneous velocity from a mouse. No timeout argument to pass as it does not seem to do anything.

        Returns
        -------
        tuple

        """
        x, y = 0, 0
        TIMEOUT = 1  # This does not seem to change anything as long as it is > 1
        try:
            readout = [dat for dat in self.dev.interruptRead(0x81, 8, TIMEOUT)]
            y = _u2s(readout[2], readout[3])
            x = _u2s(readout[4], readout[5])
        except usb1.USBErrorTimeout:
            pass

        return MouseVelocityData(x=x, y=y)


if __name__ == "__main__":
    from datetime import datetime

    mouse0, mouse1 = Mouse(ind=0), Mouse(ind=1)

    COUNTER = 10000
    pos_arr = np.empty((5, COUNTER))
    t0 = datetime.now()
    for i in range(COUNTER):
        if i % 100 == 0:
            print(i)
        x0, y0 = mouse1.read_velocity()
        x1, y1 = mouse1.read_velocity()
        pos_arr[:, i] = (x0, x1, y0, y1, (datetime.now() - t0).total_seconds())
        t0 = datetime.now()
    pos_arr[4, :] = np.cumsum(pos_arr[4, :])

    np.save(r"C:\Users\SNeurobiology\Documents\Luigi\vr-test\mousetest2.npy", pos_arr)
