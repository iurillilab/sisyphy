import zmq

import numpy as np

from sisyphy.estimators.base import Estimator

TIMEOUT = 0.001  # timeout for waiting for data request


def _normalize(val):
    return max(min(int(val) + 127, 255), 0)


class ZeroMQEstimator(Estimator):
    def __init__(self, *args, address: str = "127.0.0.1", port: int = 5678, **kwargs):
        """Estimator that communicate the average velocities when queried on a TCP port.

        Parameters
        ----------
        address : str
        port
        """
        super(ZeroMQEstimator, self).__init__(*args, **kwargs)

        self.address = address
        self.port = port

    def run(self):
        """We overwrite the whole run method to manage the socket context."""

        with zmq.Context() as context:
            sock = context.socket(zmq.REP)
            # s.bind((self.address, self.port))
            # s.listen()
            # conn, addr = s.accept()
            # conn.settimeout(0.001)
            sock.bind(f"tcp://{self.address}:{self.port}")

            while not self.kill_event.is_set():
                self.fetch_data()  # let the queue reading go
                #try:
                data = sock.recv(1024, zmq.NOBLOCK)
                print(data)
                if data == b"read_velocities":
                    print("sending")
                    velocities_df = self.average_values
                    if len(velocities_df) > 0:
                        pitch, yaw, roll = self.average_values.pitch, self.average_values.yaw, self.average_values.roll
                    else:
                        pitch, yaw, roll = (0, 0, 0)
                    print("sending", f"{_normalize(pitch)},{_normalize(yaw)},{_normalize(roll)}")
                    sock.send_string(f"{_normalize(pitch)},{_normalize(yaw)},{_normalize(roll)}")

                if not data:
                    break
                #except:
                #    pass

if __name__ == "__main__":
    from multiprocessing import Event
    from time import sleep

    from sisyphy.sphere_velocity import SphereVelocityProcess

    kill_event = Event()
    mouse_process = SphereVelocityProcess(kill_event=kill_event)
    p = ZeroMQEstimator(sphere_data_queue=mouse_process.data_queue, kill_event=kill_event)
    mouse_process.start()
    p.start()
    # sleep(10)
    # kill_event.set()
    mouse_process.join()
    # sleep(0.5)

    p.join()
