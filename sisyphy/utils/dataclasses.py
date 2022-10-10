import time
from dataclasses import dataclass, field


@dataclass
class TimestampedDataClass:
    t_ns: int = field(default_factory=time.time_ns, init=False)
