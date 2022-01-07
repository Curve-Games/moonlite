import tkinter as tk
from tkinter import messagebox, ttk
from typing import Type

from moonlite.discounts import DiscountsScraper
from moonlite.grant_package import GrantPackage
from moonlite.insights_scraper import InsightsScraper
from moonlite.keychecker import Keychecker

TOOLKIT = [
    {"name": "Keychecker", "start": Keychecker},
    {"name": "Insights Scraper", "start": InsightsScraper},
    {"name": "Discount History Scraper", "start": DiscountsScraper},
    {"name": "Grant Packages (WIP)", "start": GrantPackage},
]

class StartApp(tk.Tk):
    def __init__(self, start_page: Type[tk.Frame] = None):
        tk.Tk.__init__(self)
        self.minsize(300, 200)
        self.maxsize(600, 400)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.start_page = StartPage
        if start_page is not None:
            self.start_page = start_page

        self._frame: tk.Frame = None
        self.switch_frame(self.start_page)

    def switch_frame(self, frame_class):
        new_frame = frame_class(self)
        if self._frame is not None:
            self._frame.destroy()
        self._frame = new_frame
        self.pack_propagate(0)
        self._frame.grid(row=0, column=0, sticky='news')

class StartPage(tk.Frame):
    def __init__(self, master):
        master.minsize(300, 300)
        master.maxsize(300, 300)

        self.master = master
        tk.Frame.__init__(self, master, width=300, height=200)
        self.columnconfigure(0, weight=1, minsize=250)
        for i, tool_dict in enumerate(TOOLKIT):
            self.rowconfigure(i, weight=1, minsize=50)
            wrapper = tk.Frame(master=self)
            wrapper.grid(row=i, column=0, padx=10, pady=10, sticky='news')
            btn = tk.Button(master=wrapper, text=tool_dict['name'], command=lambda tool_dict=tool_dict: self._change_frames(tool_dict))
            btn.pack(fill=tk.BOTH, expand=True)

    def _change_frames(self, tool_dict):
        if 'WIP' not in tool_dict['name']:
            self.master.switch_frame(tool_dict['start'])
        else:
            messagebox.showinfo(f'\"{tool_dict["name"]}\" is a work in progress', f'{tool_dict["name"]} is a work in progress')

class DownloadDialog(tk.Frame):
    def __init__(self, master):
        master.minsize(300, 100)
        master.maxsize(300, 100)

        tk.Frame.__init__(self, master, width=300, height=100)
        self.rowconfigure([0, 1], weight=1, minsize=50)
        self.columnconfigure(0, weight=1, minsize=300)

        # We create a StringVar that we can update with the current status, as well as a label to "store" it in
        self.status_text = tk.StringVar()
        self.status_text.set("Downloading...")
        self.status = tk.Label(self, textvariable=self.status_text)
        self.status.grid(row=0, column=0, padx=2, pady=2, sticky='news')

        # We also create a progress bar for the download progress
        self.download_progress = ttk.Progressbar(self, orient=tk.HORIZONTAL, mode='determinate')
        self.download_progress.grid(row=1, column=0, padx=2, pady=2, sticky='news')

    def update_dialog(self, total, downloaded, status: str):
        # Update the dialog with the new progress bar position and status
        self.download_progress['value'] = downloaded / total
        self.status_text.set(status)

class Moonlite:
    @staticmethod
    def run():
        app = StartApp()
        app.mainloop()

    @staticmethod
    def download(total):
        app = StartApp(start_page=DownloadDialog)
        app.mainloop()
        return app, lambda downloaded, status: app._frame.update_dialog(total, downloaded, status)

if __name__ == '__main__':
    Moonlite.run()
