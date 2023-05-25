# Small interface to stop the streaming process when a button is pressed.

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
        self.stop_button.clicked.connect(self.streamer.stop)
        layout = QVBoxLayout()
        layout.addWidget(self.stop_button)
        self.setLayout(layout)



if __name__ == "__main__":
    app = QApplication([])
    streamer = MouseSphereDataStreamer(data_path=r"E:\Luigi\Test")
    stop_button = StopButton(streamer)
    stop_button.show()
    app.exec_()
