import socket

import numpy as np

from sisyphy.streamers.base import SocketStreamer

TIMEOUT = 0.001  # timeout for waiting for data request


def _normalize(val):
    return max(min(int(val) + 127, 255), 0)


def _prepare_for_tcp(velocities):
    return bytes([_normalize(velocities.pitch), _normalize(velocities.yaw)])


class TcpMouseStreamer(SocketStreamer):
    """Estimator that communicate the average velocities when queried on a TCP port."""

    def __init__(self, *args, address: str = "127.0.0.1", port: int = 65432, **kwargs):
        """

        Parameters
        ----------
        address : str
        port
        """
        super(TcpMouseStreamer, self).__init__(*args, **kwargs)

        self.address = address
        self.port = port

    def run(self):
        """We overwrite the whole run method to manage the socket context."""

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.address, self.port))
            s.listen()
            conn, addr = s.accept()
            conn.settimeout(0.001)
            with conn:
                print(f"Connected by {addr}")
                while not self.kill_event.is_set():
                    self.fetch_data()  # let the queue reading go
                    try:
                        data = conn.recv(1024)

                        if data == bytes(self.query_string):
                            if len(self.average_values) > 0:
                                print(
                                    "sending",
                                    self.average_values.yaw,
                                    self.average_values.pitch,
                                )
                                conn.sendall(_prepare_for_tcp(self.average_values))
                            else:
                                conn.sendall(bytes([0, 0]))

                        if not data:
                            break
                    except socket.timeout:
                        pass
                    print("looping idle")


if __name__ == "__main__":
    from multiprocessing import Event
    from time import sleep

    from sisyphy.sphere_velocity import SphereVelocityProcess

    kill_event = Event()
    mouse_process = SphereVelocityProcess(kill_event=kill_event)
    p = TcpMouseStreamer(
        sphere_data_queue=mouse_process.data_queue, kill_event=kill_event
    )
    mouse_process.start()
    p.start()
    # sleep(10)
    # kill_event.set()
    mouse_process.join()
    # sleep(0.5)

    p.join()
