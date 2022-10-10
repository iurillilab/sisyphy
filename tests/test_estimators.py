from time import sleep
from multiprocessing import Event
from sisyphy.estimators import Estimator
from sisyphy.sphere_velocity import DummyVelocityProcess


def test_base_estimator():
    kill_event = Event()
    mouse_process = DummyVelocityProcess(kill_event=kill_event)
    p = Estimator(sphere_data_queue=mouse_process.data_queue, kill_event=kill_event)
    mouse_process.start()
    p.start()
    sleep(3)
    kill_event.set()
    mouse_process.join()
    sleep(0.5)


    p.join()