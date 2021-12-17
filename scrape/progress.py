import concurrent.futures
import queue
import traceback
from abc import ABC, abstractmethod
from inspect import signature
from tkinter import messagebox
from typing import Union, Type

from utils.dashboard import CookiesNotFound


class Progress(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def update(self, n: int = 1):
        pass

    @abstractmethod
    def close(self):
        pass

class StopException(Exception):
    pass

def shutdown_executor(executor):
    executor.shutdown(wait=False)
    while True:
        # cancel all waiting tasks
        try:
            work_item = executor._work_queue.get_nowait()
        except queue.Empty:
            break
        if work_item is not None:
            work_item.future.cancel()
    raise StopException

def get_exec_results(futures: list, executor, progress: Union[Type[Progress], Progress] = None):
    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()
            if isinstance(progress, Progress):
                progress.update()
        except Exception as exc:
            print('Exception occurred:', exc, type(exc))
            print(progress, progress.__class__)
            # We create an exception InsightsProgress to signal to the caller that an exception has occurred
            if isinstance(progress, Progress):
                sig = signature(progress.__class__.__init__)
                progress.__class__(*list(range(len(sig.parameters) - 2)), exception=exc)
            else:
                sig = signature(progress)
                progress(*list(range(len(sig.parameters) - 1)), exception=exc)
            # We also shutdown the executor
            print(f'Shutting down {executor}')
            shutdown_executor(executor)

EXCEPTION_HANDLERS = {
    StopException: lambda e: None,
    CookiesNotFound: lambda e: messagebox.showinfo('Cannot find required cookies', 'Cannot find required cookies. Try refreshing Steamworks dashboard/selecting a different browser.'),
    'default': lambda e: messagebox.showerror(f'{e} has occurred', f"Unhandled error occurred.\nTraceback:\n{''.join(traceback.format_exception(etype=type(e), value=e, tb=e.__traceback__))}")
}