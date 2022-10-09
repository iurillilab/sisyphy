from dataclasses import dataclass, field
import time

@dataclass
class TimestampedDataClass:
    t_ns: int = field(default_factory=time.time_ns, init=False)