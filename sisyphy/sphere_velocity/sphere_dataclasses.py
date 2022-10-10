from dataclasses import dataclass

from sisyphy.utils.dataclasses import TimestampedDataClass


@dataclass
class MouseVelocityData(TimestampedDataClass):
    x: float
    y: float


@dataclass
class RawMiceVelocityData:
    mouse0: MouseVelocityData
    mouse1: MouseVelocityData


@dataclass
class EstimatedVelocityData(TimestampedDataClass):
    pitch: float
    roll: float
    yaw: float
