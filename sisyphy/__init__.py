# Author: Luigi Petrucco @ iurilli lab
# Contact: luigi [dot] petrucco [at] iit [dot] it

"""Minimal code to acquire speed from a spherical treadmill."""

__all__ = ["SphereDataStreamer", "MouseSphereDataStreamer", "MockDataStreamer"]

from sisyphy.core import (
    MockDataStreamer,
    MouseSphereDataStreamer,
    SphereDataStreamer,
)
