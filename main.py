import tkinter as tk

from grant_package import GrantPackage
from insights_scraper import InsightsScraper

from keychecker import Keychecker

TOOLKIT = [
    {"name": "Keychecker", "start": Keychecker},
    {"name": "Insights Scraper", "start": InsightsScraper},
    {"name": "Grant Packages", "start": GrantPackage}
]

class StartApp(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.minsize(300, 200)
        self.maxsize(600, 400)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.start_page = StartPage

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
        master.minsize(300, 200)
        master.maxsize(300, 200)

        tk.Frame.__init__(self, master, width=300, height=200)
        self.columnconfigure(0, weight=1, minsize=250)
        for i, tool_dict in enumerate(TOOLKIT):
            self.rowconfigure(i, weight=1, minsize=50)
            wrapper = tk.Frame(master=self)
            wrapper.grid(row=i, column=0, padx=10, pady=10, sticky='news')
            btn = tk.Button(master=wrapper, text=tool_dict['name'], command=lambda tool_dict=tool_dict: master.switch_frame(tool_dict['start']))
            btn.pack(fill=tk.BOTH, expand=True)


if __name__ == '__main__':
    app = StartApp()
    app.mainloop()
