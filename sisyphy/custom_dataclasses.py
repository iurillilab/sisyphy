from dataclasses import dataclass, field
import time


@dataclass
class TimeStampData:
    t_ns: int
    code: int

@dataclass
class _TimestampedDataClass:
    t_ns: int = field(default_factory=time.time_ns, init=False)


@dataclass
class MouseVelocityData(_TimestampedDataClass):
    x: int
    y: int


@dataclass
class RawMiceVelocityData:
    mouse0: MouseVelocityData
    mouse1: MouseVelocityData


@dataclass
class EstimatedVelocityData(_TimestampedDataClass):
    pitch: float
    roll: float
    yaw: float
