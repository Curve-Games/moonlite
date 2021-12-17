from datetime import date, timedelta
import os
import time
import tkinter as tk
from tkinter import TclError, ttk
from pathlib import Path
import threading
from typing import Dict

from tkcalendar import DateEntry
from tkinter import filedialog, messagebox
from scrape.insights import insights_scrape
from scrape.progress import Progress, EXCEPTION_HANDLERS

from utils.browsers import BrowserTypes
from utils.time import DATE_FORMAT


class InsightsScraper(tk.Frame):
    def __init__(self, master):
        print('Insights scraper')
        self.save_directory: Path = Path(os.getcwd()).joinpath('CSVs')
        self.progress_bars: Dict[int, ] = dict()
        self.scrape_thread = None
        self.stop_event = threading.Event()
        self.buttons: Dict[str, tk.Button] = dict()
        self.loading_frame = None

        master.minsize(800, 300)
        master.maxsize(1200, 450)
        tk.Frame.__init__(self, master=master, width=800, height=300)
        self.columnconfigure(0, weight=1, minsize=800)
        self.rowconfigure(0, weight=1, minsize=70)
        self.rowconfigure(1, weight=1, minsize=230)

        top_frame = tk.Frame(master=self, relief=tk.RAISED)
        top_frame.grid(row=0, column=0, sticky='news')
        top_frame.columnconfigure(0, weight=1, minsize=800)
        top_frame.rowconfigure([0, 1], weight=1, minsize=35)

        date_frame = tk.Frame(master=top_frame)
        date_frame.grid(row=0, column=0, sticky='news')
        date_frame.columnconfigure(0, weight=1, minsize=50)
        date_frame.columnconfigure([1, 2], weight=1, minsize=375)
        date_frame.rowconfigure(0, weight=1, minsize=35)
        self.buttons['back'] = tk.Button(master=date_frame, text='Back', command=lambda: master.switch_frame(master.start_page))
        self.buttons['back'].grid(row=0, column=0, padx=2, pady=2, sticky='news')
        yesterday = date.today() - timedelta(days=1)
        self.from_date = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
        self.from_date.set_date(yesterday)
        self.from_date.grid(row=0, column=1, padx=2, pady=2, sticky='news')
        self.to_date = DateEntry(date_frame, width=12, background='darkblue', foreground='white', borderwidth=2)
        self.to_date.set_date(yesterday)
        self.to_date.grid(row=0, column=2, padx=2, pady=2, sticky='news')

        options_frame = tk.Frame(master=top_frame)
        options_frame.grid(row=1, column=0, sticky='news')
        options_frame.rowconfigure(0, weight=1, minsize=35)
        options_frame.columnconfigure(0, weight=1, minsize=450)
        options_frame.columnconfigure(1, weight=1, minsize=50)
        options_frame.columnconfigure(2, weight=1, minsize=200)
        options_frame.columnconfigure(3, weight=1, minsize=100)

        self.save_location = tk.Entry(master=options_frame)
        self.save_location.grid(row=0, column=0, padx=2, pady=2, sticky='news')
        self.save_location.insert(0, str(self.save_directory))

        self.buttons['open'] = tk.Button(master=options_frame, text='Open', command=lambda: self._set_save_directory())
        self.buttons['open'].grid(row=0, column=1, padx=2, pady=2, sticky='news')
        self.browsers = tk.StringVar(master=options_frame)
        browser_list = list(BrowserTypes)
        self.browsers.set(browser_list[0].name)
        self.browser_dropdown = tk.OptionMenu(options_frame, self.browsers, *[b.name for b in browser_list])
        self.browser_dropdown.grid(row=0, column=2, padx=2, pady=2, sticky='news')
        self.buttons['start'] = tk.Button(master=options_frame, text='Start', command=lambda: self._toggle_scrape())
        self.buttons['start'].grid(row=0, column=3, padx=2, pady=2, sticky='news')

        # Create a scrollable frame for our progress bars
        self.bottom_frame = ttk.Frame(self, relief=tk.SUNKEN)
        self.bottom_frame.grid(row=1, column=0, padx=2, pady=2, sticky='news')
        canvas = tk.Canvas(self.bottom_frame)
        scrollbar = ttk.Scrollbar(self.bottom_frame, orient='vertical', command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        self.scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.bind(
            '<Configure>',
            lambda e: canvas.itemconfigure("self.scrollable_frame", width=e.width)
        )
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor='nw', tags='self.scrollable_frame')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

    def _set_save_directory(self):
        self.save_directory = Path(filedialog.askdirectory(initialdir=str(self.save_directory)))

    def _set_buttons_state(self, state):
        for button in self.buttons:
            self.buttons[button]['state'] = state

    def _cleanup(self):
        self.stop_event.set()
        self._set_buttons_state(tk.DISABLED)

    def _destroy_progress(self):
        for appid in self.progress_bars:
            self.progress_bars[appid].master.destroy()
        self.progress_bars = dict()

    def _toggle_scrape(self):
        if self.to_date.get_date() < self.from_date.get_date():
            messagebox.showinfo('Invalid date range', f'Invalid date range. To date cannot be before from date ({self.from_date.get_date()} -> {self.to_date.get_date()})')
            self.to_date.set_date(self.from_date.get_date())
        else:
            # If scrape thread is None then we start the scrape
            if self.scrape_thread is None:

                # We destroy all the progress bars left from the previous scrape
                self._destroy_progress()
                self.stop_event.clear()

                # We also set the Open and Back buttons to a disabled state as well as browser drop down to disabled
                self.browser_dropdown['state'] = tk.DISABLED
                self.buttons['open']['state'] = tk.DISABLED
                self.buttons['back']['state'] = tk.DISABLED

                # Creating an indeterminate loading bar to inform the user that we have started looking for cookies and apps
                self.loading_frame = tk.Frame(master=self.bottom_frame)
                self.loading_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER, relwidth=0.75, relheight=0.3)
                loading_label = tk.Label(self.loading_frame, text='Fetching cookies and apps...')
                loading_label.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
                loading_progress = ttk.Progressbar(self.loading_frame, length=100, orient=tk.HORIZONTAL, mode='indeterminate')
                loading_progress.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
                loading_progress.start()

                this = self  # We set a variable to self in order to use it within TkinterProgress

                # Define an implementation of InsightsProgress that will update a ProgressBar widget
                class TkinterProgress(Progress):
                    def __init__(self, appid: int, days: int, ord: int, out_of: int, min_date: date, max_date: date, exception: Exception = None):
                        try:
                            if this.loading_frame is not None:
                                progress: ttk.Progressbar = next(filter(
                                    lambda child: isinstance(child, ttk.Progressbar) and hasattr(child, 'stop'),
                                    this.loading_frame.winfo_children()
                                ))
                                progress.stop()
                                this.loading_frame.destroy()
                                this.loading_frame = None
                        except TclError:
                            # We catch and ignore any TclErrors due to the multithreading madness going on
                            pass

                        if exception is None:
                            self.appid = appid
                            self.day = 0
                            self.days = days
                            self.ord = ord
                            self.out_of = out_of
                            self.min_date = min_date
                            self.max_date = max_date
                            if appid not in this.progress_bars:
                                progress_frame = tk.Frame(this.scrollable_frame)
                                progress_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=True)
                                progress_frame.rowconfigure(0, weight=1, minsize=20)
                                progress_frame.columnconfigure([0, 1], weight=1, minsize=390)
                                progress_label = tk.Label(
                                    progress_frame,
                                    text=f'{ord + 1}/{out_of}: {appid} ({min_date.strftime(DATE_FORMAT)} -> {max_date.strftime(DATE_FORMAT)})',
                                    anchor='w'
                                )
                                progress_label.grid(row=0, column=0, padx=2, pady=2, sticky='news')
                                progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
                                progress_bar.grid(row=0, column=1, padx=2, pady=2, sticky='news')
                                this.progress_bars[appid] = progress_bar
                        else:
                            # If the progress to be started is an exception then we will display the exception
                            # and cleanup if we aren't doing so already
                            if not this.stop_event.is_set():
                                this._cleanup()
                            EXCEPTION_HANDLERS.get(exception.__class__, EXCEPTION_HANDLERS['default'])(exception)

                    def update(self, n: int = 1):
                        this.update_idletasks()
                        self.day += n
                        this.progress_bars[self.appid]['value'] += (100 / self.days) * n

                    def close(self):
                        # progress_bars[self.appid].destroy()
                        pass

                # Start the insights scraping in a separate thread
                self.scrape_thread = threading.Thread(name='Scraper', target=lambda: insights_scrape(
                    self.save_directory,
                    BrowserTypes[self.browsers.get()],
                    self.from_date.get_date(),
                    self.to_date.get_date(),
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
                    self.scrape_thread = None
                    self._set_buttons_state(tk.NORMAL)
                    self.buttons['start'].config(text='Start')
                    self.browser_dropdown['state'] = tk.NORMAL

                threading.Thread(target=watcher, name='Watcher').start()
            else:
                # Otherwise, we initiate cleanup
                self._cleanup()
