import abc
import warnings
from datetime import datetime
from multiprocessing import Event, Process, Queue
from pathlib import Path
from time import time_ns

import pandas as pd


class DataStreamer(Process, metaclass=abc.ABCMeta):
    """General streamer of data from a SphereReaderProcess, implementing some utils
    to accumulate data over time, and (in subclasses) to stream data to other processes.
    """

    def __init__(
        self,
        *args,
        time_to_avg_s: float = 0.100,
        kill_event: Event = None,
        sphere_data_queue=None,
        output_queue=None,
        data_path: str = None,
        **kwargs,
    ):
        """
        Parameters
        ----------
        time_to_avg_s : float
            Duration of the window over which to average.
        kill_event : Event
            Termination event.
        sphere_data_queue : Queue
            Queue to read data from.
        output_queue : Queue
            Queue to write data to.

        """
        super().__init__(*args, **kwargs)

        self.kill_event = kill_event if kill_event is not None else Event()
        self._sphere_data_queue = sphere_data_queue
        self.output_queue = output_queue if output_queue is not None else Queue()

        self._time_to_avg_s = time_to_avg_s
        self.data_path = Path(data_path) if data_path is not None else None

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
                # print(i, len(self._past_times) - i)
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
        data_df = pd.DataFrame(self._past_data_list[self._last_past_idx :])
        return data_df.mean()

    def execute_in_run_loop(self):
        pass

    def save_data(self):
        if self.data_path is None:
            return
        self.data_path.mkdir(parents=True, exist_ok=True)
        data_df = pd.DataFrame(self._past_data_list)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        data_df.to_csv(self.data_path / f"{timestamp}_data.csv")
        print(f"Saved data to {self.data_path}.")

    def run(self) -> None:
        print("running streamer process.")
        self.t_start = time_ns()
        i = 0
        while not self.kill_event.is_set():
            self.fetch_data()
            self.execute_in_run_loop()

            # Some printing:
            if i % 1000 == 0:
                avg_vals = self.average_values
                if len(avg_vals) > 0:
                    vals_dict = avg_vals.to_dict()
                    data_string = "".join(
                        [f"{key}: {val}  - " for key, val in vals_dict.items()]
                    )
                    #print(f"Average values: {data_string}")

                    # self.output_queue.put(avg_vals)
                    # print(self.output_queue)
            i += 1

        self.save_data()


class SocketStreamer(DataStreamer, metaclass=abc.ABCMeta):
    """Stream velocities over a socket connection to implement in subclasses."""

    def __init__(self, address, port, query_string="read_velocities"):
        self.address = address
        self.port = port
        self.query_string = query_string
        super().__init__()
