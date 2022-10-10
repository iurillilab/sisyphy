from multiprocessing import get_context
from multiprocessing.queues import Queue
from queue import Empty, Full
from typing import Union


class SaturatingQueue(Queue):
    def __init__(self, *args, maxsize: int = 10000, **kwargs):
        # if maxsize is None:
        #     raise TypeError("You must specify a maximum size for a SaturatingQueue!")
        super(SaturatingQueue, self).__init__(
            *args, maxsize=maxsize, ctx=get_context(), **kwargs
        )

    def put(self, *args, verbose: bool = False, **kwargs) -> None:
        try:
            super().put(*args, **kwargs, block=False)
        except Full:
            if verbose:
                print("Full queue!")  # TODO: replace with meaningful log

    def get_all(self, *args, **kwargs):
        all_data = []

        while True:
            try:
                all_data.append(
                    super(SaturatingQueue, self).get(*args, block=False, **kwargs)
                )
            except Empty:
                break

        return all_data

    def clear(self) -> None:
        """Clear queue. might hang for super long queues!"""
        try:
            while True:
                self.get(block=False)
        except Empty:
            pass

    def tear_down(self) -> None:
        """Clear queue and join thread for good measure."""
        self.clear()
        self.close()
        self.join_thread()
