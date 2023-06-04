# Small interface to stop the streaming process when a button is pressed.
from time import sleep
from sisyphy.core import MouseSphereDataStreamer

from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget


class StopButton(QWidget):
    def __init__(self, streamer):
        super().__init__()
        self.streamer = streamer
        self.initUI()

        self.streamer.start()


    def initUI(self):
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.close)

        layout = QVBoxLayout()
        layout.addWidget(self.stop_button)
        self.setLayout(layout)

    def closeEvent(self, event):
        self.streamer.stop()
        event.accept()

    def close(self):
        self.streamer.stop()
        super().close()


if __name__ == "__main__":
    app = QApplication([])
    streamer = MouseSphereDataStreamer(data_path=r"E:\Luigi")
    stop_button = StopButton(streamer)
    stop_button.show()
    app.exec_()
