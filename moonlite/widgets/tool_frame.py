import threading
import tkinter as tk
from abc import abstractmethod
from typing import Dict


class ToolFrame(tk.Frame):
    def __init__(self, master, minsize_x: int = 800, minsize_y: int = 300, maxsize_x: int = 1200, maxsize_y: int = 450):
        self.scrape_thread = None
        self.stop_event = threading.Event()
        self.buttons: Dict[str, tk.Button] = dict()

        master.minsize(minsize_x, minsize_y)
        master.maxsize(maxsize_x, maxsize_y)
        tk.Frame.__init__(self, master=master, width=800, height=300)
        self.columnconfigure(0, weight=1, minsize=800)
        self.rowconfigure(0, weight=1, minsize=70)
        self.rowconfigure(1, weight=1, minsize=230)

    def _set_buttons_state(self, state):
        for button in self.buttons:
            self.buttons[button]['state'] = state

    def _cleanup(self):
        self.stop_event.set()
        self._set_buttons_state(tk.DISABLED)

    @abstractmethod
    def _destroy_progress(self):
        pass

    @abstractmethod
    def _toggle_scrape(self):
        pass
