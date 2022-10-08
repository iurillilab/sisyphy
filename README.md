# sisyphy
Minimal code for handling acquisition of position from ball and some acquisition synch tools

## WIP notes

### Mouse reading
To read mouse in python:

1) figure out vendor and device id. The following could help, knowing ie the Logitech vendor id (`0x046d`):

```python
import usb1
iGIdVendor = 0x046d  # Logitech id
ctx = usb1.LibUSBContext()
alldevs = ctx.getDeviceList()
print([dev for dev in alldevs if dev.getVendorID()==iGIdVendor])  # list ids of Logitech devices
```

2) Replace the device drivers with standard WinUSB. This was done using the intuitive [Zadig interface](https://zadig.akeo.ie/). From the website there are extensive tutorials reachable.

3) At this point, with the little script `readmouse.py` we can read mouse motion! As a nice side effect, replacing the mouse drivers stops the normal functioning of the mouse for the OS.

**Note:** This was done and tested with LogiTech502 mouse, and works specifically with a pair of mice of that model!

