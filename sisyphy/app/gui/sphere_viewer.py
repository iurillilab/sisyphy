"""
Simple examples demonstrating the use of GLMeshItem.
"""

import os
from datetime import datetime
from multiprocessing import Process, freeze_support


import numpy as np
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtGui

from sisyphy import MockDataStreamer

app = pg.mkQApp("GLMeshItem Example")

class CustomGLViewWidget(gl.GLViewWidget):
    def __init__(self, *args, kill_event, **kwargs):
        super().__init__(*args, **kwargs)
        self.kill_event = kill_event

    def closeEvent(self, ev):
        super().closeEvent(ev)
        self.kill_event.set()
        print("set")


class PLT:
    def __init__(self, kill_event):
        w = CustomGLViewWidget(kill_event=kill_event)
        w.show()
        w.setWindowTitle("pyqtgraph example: GLMeshItem")
        w.setCameraPosition(distance=4)

        g = gl.GLGridItem()
        g.scale(2, 2, 1)
        w.addItem(g)

        md = gl.MeshData.sphere(rows=20, cols=20)
        colors = np.ones((md.faceCount(), 4), dtype=float)
        colors[:, :3] = np.array(
            [
                np.linspace(0, 1, colors.shape[0]),
            ]
            * 3
        ).T
        colors[::2, 0] = 0
        md.setFaceColors(colors)
        self.m3 = gl.GLMeshItem(meshdata=md, smooth=False)
        w.addItem(self.m3)

    def update(self, pitch, roll, yaw):
        for ax, v in zip([(1, 0, 0), (0, 1, 0), (0, 0, 1)], [pitch, roll, yaw]):
            self.m3.rotate(v / 5, *ax)

        QtGui.QApplication.processEvents()


class receiver(Process):
    def __init__(self, data_queue, kill_evt):
        Process.__init__(self)
        self.data_queue = data_queue
        self.kill_event = kill_evt

    def run(self):
        self.p = PLT(self.kill_event)

        data = [[], [], []]
        update_i = 0
        while not self.kill_event.is_set():
            vel_data = self.data_queue.get()
            [
                d.append(val)
                for d, val in zip(data, [vel_data.pitch, vel_data.roll, vel_data.yaw])
            ]
            last_t = 10

            if update_i % last_t == 0:
                self.p.update(
                    pitch=np.mean(data[0][-last_t:]),
                    roll=np.mean(data[1][-last_t:]),
                    yaw=np.mean(data[2][-last_t:]),
                )
            update_i += 1


if __name__ == "__main__":
    from time import sleep
    from multiprocessing import Event
    print("MAIN PID: ", os.getpid())

    freeze_support()
    kill_evt = Event()

    data_streamer = MockDataStreamer(kill_event=kill_evt)
    receiv = receiver(data_queue=data_streamer.output_queue, kill_evt=kill_evt)
    data_streamer.start()
    receiv.start()

    # plt = PLT(kill_evt)




    #sleep(2)
    #data_streamer.stop()
    """
    



    
    print("MAIN PID: ", os.getpid())
    kill_evt = Event()
    # out_pipe, in_pipe = mp.Pipe()
    # p1 = CalibratedSphereReaderProcess(kill_event=kill_evt)

    p1 = MockDataStreamer(kill_event=kill_evt)

    # p1 = sender(pipe=in_pipe)
    # p2 = receiver(data_queue=p1.output_queue, kill_evt=kill_evt)
    p1.start()
    
    # p2.start()
    print("started")


# if __name__ == '__main__':
#     pg.exec()
"""