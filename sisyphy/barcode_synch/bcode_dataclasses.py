from dataclasses import dataclass


@dataclass
class TimeStampData:
    t_ns_buffer_stream: int
    t_ns_code: int
    code: int
