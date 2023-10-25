# Small interface to stop the streaming process when a button is pressed.
from collections.abc import Callable, Iterable, Mapping
from time import sleep
from typing import Any
from queue import Empty
from collections import deque
from sisyphy.core import MouseSphereDataStreamer
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QPushButton
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from multiprocessing import Process, Queue, Event
import qdarkstyle  # Import qdarkstyle
import time

from arrayqueues import ArrayQueue, TimestampedArrayQueue

import numpy as np


class StopButton(QMainWindow):
    def __init__(self, streamer, ingestor,
                 stream_window=None):
        super().__init__()
        self.streamer = streamer
        self.ingestor = ingestor
        
        self.initUI()

        self.stream_window = stream_window

        self.ingestor.start()
        self.streamer.start()


        if stream_window is not None:
            self.stream_window.show()


    def initUI(self):
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.stop_button)
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def closeEvent(self, event):
        self.streamer.stop()
        event.accept()

    def close(self):
        self.streamer.stop()
        if self.stream_window is not None:
            self.stream_window.close()
        super().close()


class DataQueueIngestor(Process):
    def __init__(self, data_queue: Queue,
                 query_queue: Queue, 
                 dataplot_queue: Queue,
                 running_event: Event,
                 max_history_len: float = 300000) -> None:
        
        super().__init__()
        self.data_queue = data_queue
        self.max_history_len = max_history_len
        self.query_queue = query_queue
        self.dataplot_queue = dataplot_queue
        self.running_event = running_event

        self.data_list = deque(maxlen=int(self.max_history_len))
        self.times_list = deque(maxlen=int(self.max_history_len))

    def run(self) -> None:

        # constantly retrieving all data from the queue:

        while self.running_event.is_set():
            while not self.data_queue.empty():
                data = self.data_queue.get(block=False)
                self.data_list.append(data)
                self.times_list.append(data.t_ns)

            # print("Ingested data: ", len(self.data_list))

            try:
                # constantly checking for new queries:
                query = self.query_queue.get(timeout=0.1)

                print("Got query: ", query)
                
                now_time = time.time_ns()

                # Read time to retrieve from query dict:
                time_to_retrieve = query.pop("time_interval")

                vals_to_retrieve = query.keys()

                # Retrieve data from the queue:
                first_index = 0
                for timept in self.times_list:
                    first_index += 1
                    if timept > now_time - time_to_retrieve*(10**9):
                        break
                print("First index: ", first_index, " timept: ")

                vals_to_retrieve = list(vals_to_retrieve) + ["t_ns"]
                n_heads = len(vals_to_retrieve)
                n_vals = len(self.times_list) - first_index

                if n_vals > 0 and n_heads > 0:
                    retrieved_array = np.empty((n_vals, n_heads), dtype=np.float64)

                    for head_i, head_name in enumerate(vals_to_retrieve):
                        for val_n, val_idx in enumerate(range(first_index, len(self.times_list))):
                            retrieved_array[val_n, head_i] = getattr(self.data_list[val_idx], head_name)

                    self.dataplot_queue.put(retrieved_array)
                print("Sending back: ", n_vals)

            except Empty:
                pass

                
        # Create a dict to store the retrieved data:
        #for idx in range(first_index, len(self.times_queue)):
        #    query[val].append(self.data_queue[index][val])

        # while not self.data_queue.empty():
        #     new_data = self.data_queue.get()
        #     # new_time = new_data.t_ns
        #     # if self.start_time is None:
        #     #     self.start_time = new_time
        #     # new_time = (new_time - self.start_time) / 1e9

        #     for i, attr in enumerate(self.vals_to_plot):
        #         new_y = getattr(new_data, attr)
        #         new_y = min(new_y, self.max_val)
        #         if len(self.data_y[i]) > self.rolling_buff:
        #             new_y = (new_y + sum(self.data_y[i][-self.rolling_buff:])) / (self.rolling_buff + 1)
        #         self.data_y[i].append(new_y)
        #         self.data_x[i].append(new_time)  


class RealTimePlotApp(QWidget):
    def __init__(self, dataplot_queue, query_queue, running_event):
        super().__init__()
        self.vals_to_plot = ["x0", "y0", "x1", "y1"]
        self.rolling_buff = 10
        self.max_val = 255

        self.plot_time_window = 5  # Default time window in seconds

        self.setup_ui()

        self.dataplot_queue = dataplot_queue
        self.query_queue = query_queue
        self.running_event = running_event

        self.plot_widgets = []
        self.plot_curves = []
        self.data_x = [[] for _ in range(len(self.vals_to_plot))]
        self.data_y = [[] for _ in range(len(self.vals_to_plot))]

        for i in range(len(self.vals_to_plot)):
            plot_widget = pg.PlotWidget()
            self.plot_widgets.append(plot_widget)
            self.plot_curves.append(plot_widget.plot(pen='w'))


        layout = QVBoxLayout()
        self.setLayout(layout)

        for i in range(len(self.vals_to_plot)):
            layout.addWidget(self.plot_widgets[i])

        #self.setLayout(central_widget)

        # Add a slider to control the time window
        time_window_label = QLabel("Time Window (seconds):")
        self.time_window_slider = QSlider(QtCore.Qt.Horizontal)
        self.time_window_slider.setMinimum(1)
        self.time_window_slider.setMaximum(60)  # Adjust the maximum as needed
        self.time_window_slider.setValue(self.plot_time_window)
        layout.addWidget(time_window_label)
        layout.addWidget(self.time_window_slider)

        self.time_window_slider.valueChanged.connect(self.update_time_window)

        self.plot_update_enabled = True
        # Add a toggle button to start/stop updating
        self.toggle_button = QPushButton("Toggle Plot Update")
        self.toggle_button.clicked.connect(self.toggle_plot_update)
        layout.addWidget(self.toggle_button)

        # Create a timer for updating the plots
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)  # Update the plot every 100 milliseconds
        self.start_time = None

    def setup_ui(self):
        self.setWindowTitle("Real-Time Plot with Data from Process")
        self.setGeometry(100, 100, 800, 1200)

    def update_time_window(self):
        self.plot_time_window = self.time_window_slider.value()

    def toggle_plot_update(self):
        self.plot_update_enabled = not self.plot_update_enabled
        if self.plot_update_enabled:
            # self.timer.start(100)  # Start the timer
            self.toggle_button.setText("Stop Plot Update")
        else:
            # self.timer.stop()  # Stop the timer
            self.toggle_button.setText("Start Plot Update")

    def update_plot(self):
        t = time.time()
        k = 0

        # print time elapsed in seconds:
        # print("retrieving took: ", time.time() - t, " seconds, retrieved: ", k, " items")

        # Retrieve data from the queue:
        print("Sending query...")
        self.query_queue.put({"time_interval": self.plot_time_window, 
                              "x0": [], "y0": [], "x1": [], "y1": []})
        
        
        try:
            vals = self.dataplot_queue.get(timeout=0.1)
            print("Got response: ", vals[-2:, -1])
        except Empty:
            return
        if self.plot_update_enabled: # and self.start_time is not None:
            #current_time = time.time_ns()
            #current_time = (current_time - self.start_time) / 1e9

            for i in range(len(self.vals_to_plot)):
                plot_curve = self.plot_curves[i]

                # Filter data to show only the last T seconds
                #min_time = current_time - self.plot_time_window
                # print(min_time)
                #filtered_x = [x for x in self.data_x[i] if x >= min_time]
                #filtered_y = [y for j, y in enumerate(self.data_y[i]) if self.data_x[i][j] >= min_time]

                y = vals[:, i]
                x = np.arange(len(y))
                plot_curve.setData(x, y)
                HARDBOUND = 0.1
                min_y = min(min(y), -HARDBOUND)
                max_y = max(max(y), HARDBOUND)

                # Set y range to fit the data
                self.plot_widgets[i].setYRange(min_y, max_y)
                

    #def closeEvent(self, event):
    #    # Override the close event to prevent the window from closing
    #    event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    streamer = MouseSphereDataStreamer(data_path=r"E:\Luigi")
    
    _passover_queue = Queue()
    query_queue = Queue()
    dataplot_queue = ArrayQueue()
    running_event = Event()
    ingestor = DataQueueIngestor(_passover_queue, query_queue, 
                                 dataplot_queue, running_event=running_event)

    stream_window = RealTimePlotApp(query_queue=query_queue, 
                                    dataplot_queue=dataplot_queue,
                                    running_event=running_event)
    
    running_event.set()
    
    streamer.streamer._passover_queue = _passover_queue
    stop_button = StopButton(streamer=streamer,
                             ingestor=ingestor,
                             stream_window=stream_window)
    stop_button.show()

    app.aboutToQuit.connect(lambda: running_event.clear())  # Stop generator process when app is closed
    app.aboutToQuit.connect(lambda: streamer.stop())  # Stop generator process when app is closed
    app.aboutToQuit.connect(lambda: ingestor.join())  # Stop generator process when app is closed
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
