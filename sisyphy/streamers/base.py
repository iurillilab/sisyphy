import warnings
import abc
from multiprocessing import Event, Process
from time import time_ns

import pandas as pd
from sisyphy.hardware_readers import CalibratedSphereReaderProcess


class DataStreamer(Process, metaclass=abc.ABCMeta):
    """General streamer of data from a SphereReaderProcess, implementing some utils
    to accumulate data over time, and (in subclasses) to stream data to other processes.
    """
    def __init__(
        self,
        *args,
        time_to_avg_s: float = 0.100,
        kill_event: Event = None,
        sphere_data_queue = None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        time_to_avg_s : float
            Duration of the window over which to average.
        kill_event : Event
            Termination event.
        """
        super().__init__(*args, **kwargs)

        self.kill_event = kill_event if kill_event is not None else Event()

        # If there isn't already one, we start a sphere reading process:

        self._time_to_avg_s = time_to_avg_s
        self._sphere_data_queue = sphere_data_queue
        self._past_data_list = []
        self._past_times = []
        self.t_start = time_ns()

    @property
    def _last_past_idx(self):
        """Property returning the index of first element in the list to be taken to get
        a list stretching back `self._time_to_avg_s` seconds in time.
        """

        if len(self._past_times) == 0:  # avoid index problems
            return

        now = time_ns()
        i = len(self._past_times) - 1

        # Check we are not lagging behind with the queue reading:
        if now - self._past_times[i] > 5 * 1e8:
            warnings.warn(
                "More than 0.5 seconds between estimator time and last values in the queue!"
            )

        while i > 0:
            if (now - self._past_times[i]) > (self._time_to_avg_s * 1e9):
                print(i, len(self._past_times) - i)
                break
            else:
                i -= 1
        return i

    def fetch_data(self):
        """Update internal data lists."""
        retrieved_data = self._sphere_data_queue.get_all()
        self._past_data_list.extend(retrieved_data)
        self._past_times.extend([d.t_ns for d in retrieved_data])

    @property
    def average_values(self):
        data_df = pd.DataFrame(self._past_data_list[self._last_past_idx:])
        return data_df.mean()

    def execute_in_run_loop(self):
        pass

    def close(self):
        self.kill_event.set()
        self.mouse_process.join()
        sleep(0.5)

        self.join()

    def run(self) -> None:
        self.t_start = time_ns()
        i = 0
        while not self.kill_event.is_set():
            self.fetch_data()
            self.execute_in_run_loop()

            # Some printing:
            if i % 1000 == 0:
                v = self.average_values
                if len(v) > 0:
                    print(f"Average values: pitch: {v.pitch}, yaw: {v.pitch}, roll: {v.roll}")
            i += 1


class SocketStreamer(DataStreamer, metaclass=abc.ABCMeta):
    """Stream velocities over a socket connection to implement in subclasses."""
    def __init__(self, address, port, query_string="read_velocities"):
        self.address = address
        self.port = port
        self.query_string = query_string


class SphereDataStreamer:
    """Utility function that wraps together a DataStreamer and a MouseReader process, not having
    to instantiate them every time.

    Public methods:
    ---------------

        start :
            Starts the reading and the streaming process
        stop :
            Ends both processes

    """

    def __init__(self):
        self.kill_event = Event()
        self.mouse_process = CalibratedSphereReaderProcess(kill_event=self.kill_event)

        self.streamer = DataStreamer(sphere_data_queue=self.mouse_process.data_queue,
                                     kill_event=self.kill_event)

    def start(self):
        self.mouse_process.start()
        self.streamer.start()

    def stop(self):
        # streamer.close()
        self.kill_event.set()
        sleep(0.5)
        self.mouse_process.join()
        self.streamer.join()


if __name__ == "__main__":
    from time import sleep
    data_streamer = SphereDataStreamer()
    # if sphere_data_queue is None:
    data_streamer.start()
    sleep(5)
    data_streamer.stop()

