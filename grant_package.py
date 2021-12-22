import os
import tkinter as tk
from tkinter import filedialog, ttk

from widgets.highlight import Highlight
from widgets.text_placeholder import TextPlaceholder
from widgets.tool_frame import ToolFrame


class GrantPackage(ToolFrame):
    def __init__(self, master):
        super().__init__(master=master)
        self.master.geometry('800x300')
        print('Grant package page')
        self.progress_bar = None
        self.loading_frame = None

        top_frame = tk.Frame(master=self, relief=tk.RAISED)
        top_frame.grid(row=0, column=0, sticky='news')
        top_frame.columnconfigure(0, weight=1, minsize=800)
        top_frame.rowconfigure([0, 1], weight=1, minsize=35)

        options_frame = tk.Frame(master=top_frame, relief=tk.RAISED)
        options_frame.grid(row=0, column=0, sticky='news')
        options_frame.rowconfigure(0, weight=1, minsize=35)
        options_frame.columnconfigure(0, weight=1, minsize=100)
        options_frame.columnconfigure(1, weight=1, minsize=600)
        options_frame.columnconfigure(2, weight=1, minsize=50)
        options_frame.columnconfigure(3, weight=1, minsize=50)

        self.buttons['back'] = tk.Button(master=options_frame, text='Back', command=lambda: master.switch_frame(master.start_page))
        self.buttons['back'].grid(row=0, column=0, padx=2, pady=2, sticky='news')

        self.api_key = TextPlaceholder(master=options_frame, placeholder='Enter publisher API Key')
        self.api_key.grid(row=0, column=1, padx=2, pady=2, sticky='news')

        # Load and Start buttons
        self.buttons['load'] = tk.Button(master=options_frame, text='Load', command=lambda: self._load_file())
        self.buttons['load'].grid(row=0, column=2, padx=2, pady=2, sticky='news')
        self.buttons['start'] = tk.Button(master=options_frame, text='Start', command=lambda: self._toggle_scrape())
        self.buttons['start'].grid(row=0, column=3, padx=2, pady=2, sticky='news')

        self.progress_bar_frame = tk.Frame(top_frame, relief=tk.SUNKEN)
        self.progress_bar_frame.grid(row=1, column=0, padx=2, pady=2, ipadx=10, sticky='news')
        self.progress_bar_frame.rowconfigure(0, weight=1, minsize=35)
        self.progress_bar_frame.columnconfigure(0, weight=1, minsize=800)

        # Create a scrollable Text box so that the user can enter steamids
        self.bottom_frame = ttk.Frame(self, relief=tk.SUNKEN)
        self.bottom_frame.grid(row=1, column=0, padx=2, pady=2, sticky='news')
        self.bottom_frame.rowconfigure(0, weight=1, minsize=230)
        self.bottom_frame.columnconfigure(0, weight=1, minsize=800)

        self.entry = Highlight(self.bottom_frame, lambda event: self._popup_package_details(event))
        self.entry.grid(row=0, column=0, padx=2, pady=2, sticky='news')
        scrollbar = tk.Scrollbar(self.entry)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=self.entry.yview)
        self.entry.config(yscrollcommand=scrollbar.set)

    def _popup_package_details(self, event):
        info_window = tk.Toplevel(self)
        info_window.wm_overrideredirect(True)
        info_window.wm_geometry("200x50+{0}+{1}".format(event.x_root - 100, event.y_root - 25))

        label = tk.Label(info_window, text="Word definition goes here.")
        label.pack(fill=tk.BOTH)

        info_window.bind_all("<Leave>", lambda e: info_window.destroy())  # Remove popup when pointer leaves the window

    def _load_file(self):
        filepath = filedialog.askopenfilename(
            defaultextension='.txt',
            filetypes=[
                ("All Files", "*.*"),
                ("Text Documents", "*.txt")
            ],
            initialdir=os.getcwd()
        )

        if filepath:
            self.entry.foc_in()
            self.entry.delete(1.0, tk.END)
            with open(filepath, 'r') as f:
                self.entry.insert(1.0, f.read())

    def _destroy_progress(self):
        pass

    def _toggle_scrape(self):
        pass
