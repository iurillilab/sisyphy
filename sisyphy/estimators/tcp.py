from sisyphy.estimators.base import Estimator
import socket
import numpy as np


class TcpEstimator:
    def __init__(self, *args, address : str = "127.0.0.1", port : int = 65432, **kwargs):
        """Estimator that communicate the average velocities when queried on a TCP port.

        Parameters
        ----------
        address : str
        port
        """
        super(TcpEstimator, self).__init__(*args, **kwargs)

        self.address = address
        self.port = port

    def run(self):
        """We overwrite the whole run method to manage the socket context.
        """
