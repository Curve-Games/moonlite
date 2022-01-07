import traceback
from threading import Thread


class ThreadWithReturn(Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            try:
                self._return = self._target(*self._args, **self._kwargs)
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return

    def result(self):
        return self._return
