import abc
from multiprocessing import Event
from time import sleep

from sisyphy.hardware_readers import (
    CalibratedSphereReaderProcess,
    MockSphereReaderProcess,
)
from sisyphy.streamers import DataStreamer


class SphereDataStreamer(metaclass=abc.ABCMeta):
    """
    Abstract class to implement union of a SphereReaderProcess and a DataStreamer.

    Public methods:
    ---------------
    start :
        Starts the reading and the streaming process.

    stop :
        Ends both processes.

    """

    def __init__(
        self,
        kill_event=None,
        mouse_reader_process_class=None,
        data_streamer_class=None,
        data_path=None,
    ):
        self.kill_event = kill_event if kill_event is not None else Event()
        self.mouse_process = mouse_reader_process_class(kill_event=self.kill_event)
        self.streamer = data_streamer_class(
            sphere_data_queue=self.mouse_process.data_queue,
            kill_event=self.kill_event,
            data_path=data_path,
        )

        self.output_queue = self.streamer.output_queue

    def start(self):
        self.mouse_process.start()
        self.streamer.start()

    def stop(self):
        self.kill_event.set()
        sleep(0.5)
        self.mouse_process.join()

        while not self.output_queue.empty():
            self.output_queue.get()
        print("Emptied output queue.")
        while not self.mouse_process.data_queue.empty():
            self.mouse_process.data_queue.get()
        print("Emptied data queue.")

        self.streamer.kill()

        print("Killed processes.")


class MockDataStreamer(SphereDataStreamer):
    """
    Implementation of SphereDataStreamer using the MockSphereReaderProcess.
    """

    def __init__(self, **kwargs):
        super().__init__(
            mouse_reader_process_class=MockSphereReaderProcess,
            data_streamer_class=DataStreamer,
            **kwargs,
        )


class MouseSphereDataStreamer(SphereDataStreamer):
    """Implementation of SphereDataStreamer using the CalibratedSphereReaderProcess."""

    def __init__(self, **kwargs):
        super().__init__(
            mouse_reader_process_class=CalibratedSphereReaderProcess,
            data_streamer_class=DataStreamer,
            **kwargs,
        )


if __name__ == "__main__":
    from time import sleep

    data_streamer = MockDataStreamer(data_path="/Users/vigji/Desktop")
    data_streamer.start()
    sleep(5)
    data_streamer.stop()
