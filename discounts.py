import csv
import os
import threading
import time
from pathlib import Path
from tkinter import filedialog, ttk, messagebox

import tkinter as tk
from typing import List, Dict, Any

from scrape.discounts import CSV_HEADER, discounts
from scrape.progress import Progress, EXCEPTION_HANDLERS
from utils.browsers import BrowserTypes
from utils.threading import ThreadWithReturn
from widgets.tool_frame import ToolFrame

HEADER_WIDTHS = {
    'package': 70,
    'app': 70,
    'discount_id': 70,
    'from_date': 100,
    'to_date': 100,
    'name': 200,
    'description': 360,
    'percentage': 70,
    'amount': 70,
    'quantity': 70,
}

HEADER_FORMAT = {
    'package': lambda f: f,
    'app': lambda f: f,
    'discount_id': lambda f: f,
    'from_date': lambda f: f.date().isoformat().replace('-', '/'),
    'to_date': lambda f: f.date().isoformat().replace('-', '/'),
    'name': lambda f: f,
    'description': lambda f: f,
    'percentage': lambda f: f'{f}%',
    'amount': lambda f: f'-${f}',
    'quantity': lambda f: f,
}

HEADER_PRETTY = lambda header: ' '.join(h.capitalize() if h != 'id' else h.upper() for h in header.split('_'))
HEADERS_PRETTY = [HEADER_PRETTY(header) for header in CSV_HEADER]

class DiscountsScraper(ToolFrame):
    def __init__(self, master):
        super().__init__(master=master, minsize_x=1200, minsize_y=300)
        self.master.geometry('1200x300')
        print('Discounts scraper')
        self.save_directory: Path = Path(os.getcwd()).joinpath('CSVs').joinpath('discounts.csv')
        self.progress_bar = None
        self.loading_progress = None
        self.rows: List[Dict[str, Any]] = []

        top_frame = tk.Frame(master=self, relief=tk.RAISED)
        top_frame.grid(row=0, column=0, sticky='news')
        top_frame.columnconfigure(0, weight=1, minsize=800)
        top_frame.rowconfigure([0, 1], weight=1, minsize=35)

        options_frame = tk.Frame(master=top_frame, relief=tk.RAISED)
        options_frame.grid(row=0, column=0, sticky='news')
        options_frame.rowconfigure(0, weight=1, minsize=35)
        options_frame.columnconfigure(0, weight=1, minsize=50)
        options_frame.columnconfigure(1, weight=1, minsize=650)
        options_frame.columnconfigure(2, weight=1, minsize=50)
        options_frame.columnconfigure(3, weight=1, minsize=50)

        # Back, Save, and Start buttons
        self.buttons['back'] = tk.Button(master=options_frame, text='Back', command=lambda: master.switch_frame(master.start_page))
        self.buttons['back'].grid(row=0, column=0, padx=2, pady=2, sticky='news')
        self.buttons['save'] = tk.Button(master=options_frame, text='Save', command=lambda: self._save())
        self.buttons['save'].grid(row=0, column=2, padx=2, pady=2, sticky='news')
        self.buttons['save']['state'] = tk.DISABLED
        self.buttons['start'] = tk.Button(master=options_frame, text='Start', command=lambda: self._toggle_scrape())
        self.buttons['start'].grid(row=0, column=3, padx=2, pady=2, sticky='news')

        # Browser dropdown
        self.browsers = tk.StringVar(master=options_frame)
        browser_list = list(BrowserTypes)
        self.browsers.set(browser_list[0].name)
        self.browser_dropdown = tk.OptionMenu(options_frame, self.browsers, *[b.name for b in browser_list])
        self.browser_dropdown.grid(row=0, column=1, padx=2, pady=2, sticky='news')

        # Progress bar frame (underneath options)
        self.progress_bar_frame = tk.Frame(top_frame, relief=tk.SUNKEN)
        self.progress_bar_frame.grid(row=1, column=0, padx=2, pady=2, ipadx=10, sticky='news')
        self.progress_bar_frame.rowconfigure(0, weight=1, minsize=35)
        self.progress_bar_frame.columnconfigure(0, weight=1, minsize=800)

        # Create a bottom frame to hold a table
        self.bottom_frame = ttk.Frame(self, relief=tk.SUNKEN)
        self.bottom_frame.grid(row=1, column=0, padx=2, pady=2, sticky='news')
        # self.bottom_frame.rowconfigure(0, weight=1, minsize=260)
        # self.bottom_frame.columnconfigure(0, weight=1, minsize=800)

        # Create a scrollbar for the table and the table itself
        self.table_scroll = tk.Scrollbar(self.bottom_frame)
        self.table_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.table = ttk.Treeview(self.bottom_frame, yscrollcommand=self.table_scroll.set)
        self.table.pack(side=tk.LEFT, fill=tk.BOTH)

        # Populate the header
        self.table['columns'] = tuple(CSV_HEADER)
        self.table.column("#0", width=0, stretch=tk.NO)
        self.table.heading('#0', text="", anchor=tk.CENTER)
        for header in CSV_HEADER:
            self.table.column(header, width=HEADER_WIDTHS[header], stretch=tk.YES)
            self.table.heading(header, text=HEADER_PRETTY(header), anchor=tk.CENTER)

    def _save(self):
        if len(self.rows):
            self.save_directory = Path(filedialog.asksaveasfilename(
                initialdir=str(self.save_directory),
                defaultextension=".csv",
                filetypes=[("CSV file", "*.csv")]
            ))
            with open(str(self.save_directory), 'w+') as outfile:
                writer = csv.DictWriter(outfile, fieldnames=HEADERS_PRETTY)
                writer.writeheader()
                for row in self.rows:
                    writer.writerow({HEADER_PRETTY(header): str(row[header]) for header in CSV_HEADER})
        else:
            messagebox.showinfo('No rows to save', 'No rows to save')

    def _destroy_progress(self):
        for child in self.progress_bar_frame.winfo_children():
            print('destroying', child)
            child.destroy()
        self.progress_bar = None

    def _cleanup(self):
        super(DiscountsScraper, self)._cleanup()
        if self.loading_progress is not None:
            self.loading_progress.stop()
            self.loading_progress.destroy()
            self.loading_progress = None

    def _populate_table(self):
        self.table.delete(*self.table.get_children())
        if len(self.rows):
            for i, row in enumerate(self.rows):
                self.table.insert(parent='', index='end', iid=i, text='', values=[HEADER_FORMAT[col](row[col]) for col in self.table['columns']])

    def _toggle_scrape(self):
        # If scrape thread is None then we start the scrape
        if self.scrape_thread is None:
            # We destroy all the progress bars left from the previous scrape
            self._destroy_progress()
            self.stop_event.clear()

            # We also set the Save and Back buttons to be disabled, as well as browser drop down to disabled
            self.browser_dropdown['state'] = tk.DISABLED
            self.buttons['save']['state'] = tk.DISABLED
            self.buttons['back']['state'] = tk.DISABLED

            # Creating an indeterminate loading bar to inform the user that we have started looking for cookies and packages
            self.loading_progress = ttk.Progressbar(self.progress_bar_frame, length=100, orient=tk.HORIZONTAL, mode='indeterminate')
            self.loading_progress.grid(row=0, column=0, padx=2, pady=2, sticky='news')
            self.loading_progress.start()
            print("creating indeterminate bar", self.loading_progress)

            this = self  # We set a variable to self in order to use it within TkinterProgress

            # Define an implementation of Progress that will update a ProgressBar widget
            class TkinterProgress(Progress):
                def __init__(self, packages: int, exception: Exception = None):
                    try:
                        if this.loading_progress is not None:
                            this.loading_progress.stop()
                            this.loading_progress.destroy()
                            this.loading_progress = None
                    except tk.TclError:
                        # We catch and ignore any TclErrors due to the multithreading madness going on
                        pass

                    if exception is None:
                        self.packages = packages
                        self.package = 0
                        if this.progress_bar is None:
                            this.progress_bar = ttk.Progressbar(this.progress_bar_frame, orient=tk.HORIZONTAL, mode='determinate')
                            this.progress_bar.grid(row=0, column=0, padx=2, pady=2, sticky='news')
                            print("creating progress bar", this.progress_bar)
                    else:
                        # If the progress to be started is an exception then we will display the exception
                        # and cleanup if we aren't doing so already
                        if not this.stop_event.is_set():
                            this._cleanup()
                        EXCEPTION_HANDLERS.get(exception.__class__, EXCEPTION_HANDLERS['default'])(exception)

                def update(self, n: int = 1):
                    this.update_idletasks()
                    self.package += n
                    this.progress_bar['value'] += (100 / self.packages) * n

                def close(self):
                    pass

            # Start the discounts scraper in a separate thread
            self.scrape_thread = ThreadWithReturn(name='Scraper', target=lambda: discounts(
                BrowserTypes[self.browsers.get()],
                TkinterProgress,
                self.stop_event
            ))
            self.scrape_thread.start()
            # Set the start button to be a stop button
            self.buttons['start'].config(text='Stop')

            # Thread which watches the scrape_thread until completion
            def watcher():
                while True:
                    if not self.scrape_thread.is_alive():
                        break
                    time.sleep(1)
                print('scrape thread is ded')
                # We get the result from the thread
                self.rows = self.scrape_thread.result()
                if self.rows is None:
                    self.rows = []
                # Then populate the table
                self._populate_table()
                # Then cleanup
                self.scrape_thread = None
                self._set_buttons_state(tk.NORMAL)
                self.buttons['start'].config(text='Start')
                self.browser_dropdown['state'] = tk.NORMAL

            threading.Thread(target=watcher, name='Watcher').start()
        else:
            # Otherwise, we initiate cleanup
            self._cleanup()
