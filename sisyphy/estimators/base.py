from time import time_ns
from multiprocessing import Process, Event
from sisyphy.sphere_velocity import SphereVelocityProcess, DummyVelocityProcess
import warnings
import pandas as pd


class Estimator(Process):
    def __init__(self, *args, time_to_avg_s : float=0.100, kill_event : Event=None,
                 sphere_data_queue=None, **kwargs):
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
        self._time_to_avg_s = time_to_avg_s
        self._sphere_data_queue = sphere_data_queue
        self._past_data_list = []
        self._past_times = []
        self.t_start = time_ns()

    @property
    def last_past_idx(self):
        """Property returning the index of first element in the list to take
        for a list that goes self._time_to_avg_s seconds back in time.
        """

        if len(self._past_times) == 0:  # avoid index problems
            return

        now = time_ns()
        i = len(self._past_times) - 1

        # Check we are not lagging behind with the queue reading:
        if now - self._past_times[i] > 5 * 1e8:
            warnings.warn("More than 0.5 seconds between estimator time and last values in the queue!")

        while i > 0:
            if (now - self._past_times[i]) > (self._time_to_avg_s * 1e9):
                print(i, len(self._past_times) - i )
                break
            else:
                i -= 1
        return i

    def fetch_data(self):
        """Update internal data lists.
        """
        retrieved_data = self._sphere_data_queue.get_all()
        self._past_data_list.extend(retrieved_data)
        self._past_times.extend([d.t_ns for d in retrieved_data])

    @property
    def average_values(self):
        data_df = pd.DataFrame(self._past_data_list[self.last_past_idx:])
        return data_df.mean()

    def loop(self):
        """Custom code to loop in the run of the estimator to e.g. expose the velocity
        to some interface.
        """
        pass

    def run(self) -> None:
        self.t_start = time_ns()
        while not self.kill_event.is_set():
            self.fetch_data()
            self.loop()






if __name__=="__main__":
    from time import sleep
    kill_event = Event()
    mouse_process = SphereVelocityProcess(kill_event=kill_event)
    p = Estimator(sphere_data_queue=mouse_process.data_queue, kill_event=kill_event)
    mouse_process.start()
    p.start()
    sleep(100)
    kill_event.set()
    mouse_process.join()
    sleep(0.5)


    p.join()
