# Small interface to stop the streaming process when a button is pressed.
from time import sleep
from sisyphy.core import MouseSphereDataStreamer
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QPushButton
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from multiprocessing import Process, Queue, Event
import qdarkstyle  # Import qdarkstyle
import time


class StopButton(QMainWindow):
    def __init__(self, streamer, _passover_queue=None, running_event=None):
        super().__init__()
        self.streamer = streamer
        self.initUI()

        self.streamer.start()

        if _passover_queue is not None:
            self.stream_window = RealTimePlotApp(_passover_queue, running_event)
            self.stream_window.show()
        else:
            self.stream_window = None


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

class RealTimePlotApp(QWidget):
    def __init__(self, data_queue, running_event):
        super().__init__()
        self.vals_to_plot = ["x0", "y0", "x1", "y1"]
        self.rolling_buff = 10
        self.max_val = 255

        self.plot_time_window = 5  # Default time window in seconds

        self.setup_ui()

        self.data_queue = data_queue
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

        while not self.data_queue.empty():
            new_data = self.data_queue.get()
            new_time = new_data.t_ns
            if self.start_time is None:
                self.start_time = new_time
            new_time = (new_time - self.start_time) / 1e9

            for i, attr in enumerate(self.vals_to_plot):
                new_y = getattr(new_data, attr)
                new_y = min(new_y, self.max_val)
                if len(self.data_y[i]) > self.rolling_buff:
                    new_y = (new_y + sum(self.data_y[i][-self.rolling_buff:])) / (self.rolling_buff + 1)
                self.data_y[i].append(new_y)
                self.data_x[i].append(new_time)


        if self.plot_update_enabled and self.start_time is not None:
            current_time = time.time_ns()
            current_time = (current_time - self.start_time) / 1e9

            for i in range(len(self.vals_to_plot)):
                plot_curve = self.plot_curves[i]

                # Filter data to show only the last T seconds
                min_time = current_time - self.plot_time_window
                # print(min_time)
                filtered_x = [x for x in self.data_x[i] if x >= min_time]
                filtered_y = [y for j, y in enumerate(self.data_y[i]) if self.data_x[i][j] >= min_time]

                plot_curve.setData(filtered_x, filtered_y)

    #def closeEvent(self, event):
    #    # Override the close event to prevent the window from closing
    #    event.ignore()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    streamer = MouseSphereDataStreamer(data_path=r"E:\Luigi")
    _passover_queue = Queue()
    running_event = Event()
    streamer.streamer._passover_queue = _passover_queue
    stop_button = StopButton(streamer, _passover_queue, running_event)
    stop_button.show()

    app.aboutToQuit.connect(lambda: running_event.clear())  # Stop generator process when app is closed
    app.aboutToQuit.connect(lambda: streamer.stop())  # Stop generator process when app is closed

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
