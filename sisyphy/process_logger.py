""" This module has been taken from the Sashimi library (https://github.com/portugueslab/sashimi),
written by Vilim Štih.
"""

from multiprocessing import Process
import time
from pathlib import Path
from typing import Optional, TextIO
from enum import Enum, auto
from multiprocessing import Event
from typing import Optional


class ConcurrenceLogger:
    """A utility class for logging different kinds of events, periods and messages with multiprocessing"""

    def __init__(self, process_name):
        self.file: Optional[TextIO] = None
        self.process_name = process_name
        # configuration = config.read_config()
        self.root = Path(r"C:\Users\SNeurobiology\Documents\Luigi\vr-test")  # configuration["default_paths"]["log"])

    def _write_entry(self, event_type, event_id, is_sender, event_value):
        if self.file is None:
            self.file = open(self.root / (self.process_name + ".txt"), "w")
        self.file.write(
            f"{time.time_ns()},{event_type},{event_id},{'1' if is_sender else '0'},{event_value}\n"
        )
        print("written")

    def log_message(self, message):
        """Logs any kind of message"""
        self._write_entry("LOG", message, False, 0)

    def log_event(self, event_name: Enum, is_sender: bool, event_value: bool):
        """Logs multiprocessing synchronization events (multiprocessing.Event)"""
        self._write_entry(
            "EVENT", event_name.name, is_sender, "1" if event_value else "0"
        )

    def log_queue(self, queue_name, is_sender):
        """Logs queue-related events"""
        self._write_entry("QUEUE", queue_name.name, is_sender, "1")

    def close(self):
        if self.file is not None:
            self.file.flush()
            self.file.close()


class LoggingProcess(Process):
    """A process with an integrated concurrence logger
    """

    def __init__(self, *args, name, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = ConcurrenceLogger(name)

    def close_log(self):
        self.logger.close()


class TerminableProcess(Process):
    def __init__(self, kill_event : Event, *args, **kwargs):
        self.kill_event = kill_event
        super(TerminableProcess, self).__init__(*args, **kwargs)

    def run(self) -> None:
        while not self.kill_event.is_set():
            self.loop()

    def loop(self) -> None:
        pass


class LoggedEvent:
    def __init__(self, logger, name, event: Optional[Event] = None):
        super().__init__()
        if event is None:
            self.event = Event()
        else:
            self.event = event
        self.logger = logger
        self.name = name
        self.was_set = False

    def new_reference(self, logger):
        return LoggedEvent(logger, self.name, self.event)

    def set(self):
        self.event.set()
        if not self.was_set:
            self.logger.log_event(self.name, True, True)
        self.was_set = True

    def clear(self):
        self.event.clear()
        if self.was_set:
            self.logger.log_event(self.name, True, False)
        self.was_set = False

    def is_set(self):
        res = self.event.is_set()
        if res and not self.was_set:
            self.logger.log_event(self.name, False, True)
        if not res and self.was_set:
            self.logger.log_event(self.name, False, False)
        self.was_set = res
        return res