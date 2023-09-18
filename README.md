# sisyphy
Minimal code for handling data acquisition and position extraction from the spherical treadmill VR system described in [Shapcott et al, 2022](https://www.biorxiv.org/content/10.1101/2022.04.04.486889v1.full.pdf) ([here](https://www.3dneuro.com/open-hardware/spherical-treadmill/) 3D printing files & hardware instructions). 

This package is a Python-based alternative to the original Unreal Engine system. Although Python-based, it offers a set of tools to stream the data via ZeroMQ or tcp protocols, to interface it with custom applications (e.g. with MATLAB, using [ViRMEn](http://pni.princeton.edu/pni-software-tools/virmen), or [Bonsai-RX](https://bonsai-rx.org)).

The project is very much under development at the moment. Although the core components are mature and will probably be stable, there's still a lot to polish in the specifics of interfaces. It is still very open to suggestions, so feedbacks are welcome!

## Package organization

### `hardware_readers`
This module contains the interface to the hardware - the spherical threadmill and the mice that read it.

The core classes from here are:
- `RawUsbSphereReaderProcess`: process that reads raw speeds from the sphere mice and streams them in a queue.
- `CalibratedSphereReaderProcess`: process that streams calibrated data in the queue.

### `streamers`
The core abstract interface class of the package is `MouseStreamer`. It implements a process that runs and streams mouse velocities. Subclasses implement specific streamers:
- `TCPMouseStreamer`: stream mouse data using TCP protocol.
- `ZMQMouseStreamer`: stream mouse data using ZMQ.


### `mat`

The mat folder contains a MATLAB code snippet that can be used to read the TCP streamed velocities in MATLAB, to use them to control a virtual environment with the VIRmEm software.

## Time synchronization
This package also include code for synching the acquisition with Arduino-generated barcodes using the system described [here](https://optogeneticsandneuralengineeringcore.gitlab.io/ONECoreSite/projects/DAQSyncronization/) from the Optogenetics and Neural Engineering (ONE) Core at the University of Colorado School of Medicine.

In the future this code might be moved to an independent package.

## Hardware configuration

### Mouse reading
Detailled instructions on the hardware configuration can be found in the [original setup description](https://www.3dneuro.com/open-hardware/spherical-treadmill/). In brief, to make the mouse readable in Python:

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
