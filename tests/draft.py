from multiprocessing import Event

from sisyphy.process_logger import LoggingProcess, TerminableProcess


class ReceivingProcess(LoggingProcess, TerminableProcess):
    def __init__(self, log_evt: Event, *args, **kwargs):
        self.log_evt = log_evt
        super().__init__(*args, **kwargs)

    def loop(self) -> None:
        if self.log_evt.is_set(block=False):
            self.logger.log_message("TestLogProcess")
            # self.log_evt.clear()


if __name__ == "__main__":
    import time

    kill_evt = Event()
    log_evt = Event()
    p = ReceivingProcess(name="test_process", kill_event=kill_evt, log_evt=log_evt)
    p.start()
    time.sleep(0.1)
    log_evt.set()
    time.sleep(0.01)
    log_evt.clear()
    time.sleep(0.1)
    kill_evt.set()
    p.join()
