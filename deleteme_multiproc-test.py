from multiprocessing import Process, Queue, Event
from queue import Empty
import numpy as np
import time
from datetime import datetime
from arrayqueues import ArrayQueue, TimestampedArrayQueue

# Define test process class to check for speed of large dictionaries passed over queue:

class TestProcess(Process):
    def __init__(self, queue, stop_event, t_start
                 ):
        super().__init__()
        self.queue = queue
        self.stop_event = stop_event
        self.t_start = t_start
        # self.data_content = [{f"key_{i}": np.random.rand(500000) for i in range(10)} for _ in range(10)]
        self.data_content = [np.random.rand(10, int(500*j)) for j in range(1, 10)]

    def run(self):
        # Define dictionary of arrays of dict_size length with random numbers and 10 ranxom keys:
        k = 0
        while not self.stop_event.is_set():
            test_dict = self.data_content[k]
            if k == 1000:
                k = 0
            else:
                k += 1
            # t = (time.time_ns() - self.t_start)/1000000
            self.queue.put(test_dict)
            print(f"Put dict {k} on queue.")
            time.sleep(1)

        print("Test process stopped.")


# Define consumer process class to check for speed of large dictionaries passed over queue:
class ConsumerProcess(Process):
    def __init__(self, queue, stop_event, t_start
                 ):
        super().__init__()
        self.queue = queue
        self.stop_event = stop_event
        self.t_start = t_start

    def run(self):
        while not self.stop_event.is_set():
            try:
                t, test_dict = self.queue.get(timeout=0.1)
                #elapsed_t = (datetk.time_ns() - self.t_start)/1000000
                time.sleep(0.05)
                elapsed_t = datetime.now()
                print(f"Got dict from queue. Time delta: {(elapsed_t - t).microseconds/1000} ms")
            except Empty:
                pass
        print("Consumer process stopped.")


# Start processes and test speeds:

if __name__ == "__main__":
    queue = TimestampedArrayQueue(max_mbytes=1000)
    stop_event = Event()
    t_start = datetime.now() # time.time_ns()
    test_process = TestProcess(queue, stop_event=stop_event, t_start=t_start)
    consumer_process = ConsumerProcess(queue, stop_event=stop_event, t_start=t_start)
    test_process.start()
    consumer_process.start()
    time.sleep(4)
    stop_event.set()
    while not queue.empty():
        queue.get()
    test_process.join()
    consumer_process.join()
    print("Done")