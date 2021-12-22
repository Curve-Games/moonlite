import os
import time
import tkinter as tk
from tkinter import TclError, ttk, messagebox
from pathlib import Path
import threading

from tkinter import filedialog
from scrape.progress import Progress, EXCEPTION_HANDLERS
from scrape.keychecker import keychecker

from utils.browsers import BrowserTypes
from widgets.text_placeholder import TextPlaceholder
from widgets.tool_frame import ToolFrame


class Keychecker(ToolFrame):
    def __init__(self, master):
        super().__init__(master=master)
        print('Keychecker page')
        self.save_filename: Path = Path(os.getcwd()).joinpath(f'keys.csv')
        self.progress_bar = None
        self.loading_progress = None

        top_frame = tk.Frame(master=self, relief=tk.RAISED)
        top_frame.grid(row=0, column=0, sticky='news')
        top_frame.columnconfigure(0, weight=1, minsize=800)
        top_frame.rowconfigure([0, 1], weight=1, minsize=35)

        options_frame = tk.Frame(master=top_frame, relief=tk.RAISED)
        options_frame.grid(row=0, column=0, sticky='news')
        options_frame.rowconfigure(0, weight=1, minsize=40)
        options_frame.columnconfigure(0, weight=1, minsize=40)
        options_frame.columnconfigure(1, weight=1, minsize=405)
        options_frame.columnconfigure(2, weight=1, minsize=40)
        options_frame.columnconfigure(3, weight=1, minsize=40)
        options_frame.columnconfigure(4, weight=1, minsize=175)
        options_frame.columnconfigure(5, weight=1, minsize=100)

        self.buttons['back'] = tk.Button(master=options_frame, text='Back', command=lambda: master.switch_frame(master.start_page))
        self.buttons['back'].grid(row=0, column=0, padx=2, pady=2, sticky='news')

        self.save_location = tk.Entry(master=options_frame)
        self.save_location.grid(row=0, column=1, padx=2, pady=2, sticky='news')
        self.save_location.delete(0, tk.END)
        self.save_location.insert(0, str(self.save_filename))

        # Save and Load buttons
        self.buttons['save'] = tk.Button(master=options_frame, text='Save', command=lambda: self._set_save_file())
        self.buttons['save'].grid(row=0, column=2, padx=2, pady=2, sticky='news')
        self.buttons['load'] = tk.Button(master=options_frame, text='Load', command=lambda: self._load_file())
        self.buttons['load'].grid(row=0, column=3, padx=2, pady=2, sticky='news')

        self.browsers = tk.StringVar(master=options_frame)
        browser_list = list(BrowserTypes)
        self.browsers.set(browser_list[0].name)
        self.browser_dropdown = tk.OptionMenu(options_frame, self.browsers, *[b.name for b in browser_list])
        self.browser_dropdown.grid(row=0, column=4, padx=2, pady=2, sticky='news')
        self.buttons['start'] = tk.Button(master=options_frame, text='Start', command=lambda: self._toggle_scrape())
        self.buttons['start'].grid(row=0, column=5, padx=2, pady=2, sticky='news')

        # Create a scrollable Text box so that the user can enter keys
        self.bottom_frame = ttk.Frame(self, relief=tk.SUNKEN)
        self.bottom_frame.grid(row=1, column=0, padx=2, pady=2, sticky='news')
        self.bottom_frame.rowconfigure(0, weight=1, minsize=260)
        self.bottom_frame.columnconfigure(0, weight=1, minsize=800)

        self.entry = TextPlaceholder(self.bottom_frame, placeholder='Enter keys seperated by newline or click "Load"')
        self.entry.grid(row=0, column=0, padx=2, pady=2, sticky='news')
        scrollbar = tk.Scrollbar(self.entry)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=self.entry.yview)
        self.entry.config(yscrollcommand=scrollbar.set)

        self.progress_bar_frame = tk.Frame(top_frame, relief=tk.SUNKEN)
        self.progress_bar_frame.grid(row=1, column=0, padx=2, pady=2, ipadx=10, sticky='news')
        self.progress_bar_frame.rowconfigure(0, weight=1, minsize=35)
        self.progress_bar_frame.columnconfigure(0, weight=1, minsize=800)

    def _set_save_file(self):
        self.save_filename = Path(filedialog.asksaveasfilename(initialdir=str(self.save_filename)))
        self.save_location.delete(0, tk.END)
        self.save_location.insert(0, str(self.save_filename))

    def _load_file(self):
        filepath = filedialog.askopenfilename(
            defaultextension='.txt',
            filetypes=[
                ("All Files", "*.*"),
                ("Text Documents", "*.txt")
            ],
            initialdir=str(self.save_filename)
        )

        if filepath:
            self.entry.foc_in()
            self.entry.delete(1.0, tk.END)
            with open(filepath, 'r') as f:
                self.entry.insert(1.0, f.read())

    def _destroy_progress(self):
        for child in self.progress_bar_frame.winfo_children():
            print('destroying', child)
            child.destroy()
        self.progress_bar = None

    def _toggle_scrape(self):
        keys = [key.replace('\n', '') for key in self.entry.get("1.0", tk.END).split('\n') if key]
        if len(keys):
            # If scrape thread is None then we start the scrape
            if self.scrape_thread is None:
                # We destroy all the progress bars left from the previous scrape
                self._destroy_progress()
                self.stop_event.clear()

                # We also set the Save and Back buttons to a disabled state as well as browser drop down to disabled
                self.browser_dropdown['state'] = tk.DISABLED
                self.buttons['save']['state'] = tk.DISABLED
                self.buttons['back']['state'] = tk.DISABLED
                self.buttons['load']['state'] = tk.DISABLED

                # Creating an indeterminate loading bar to inform the user that we have started looking for cookies and apps
                self.loading_progress = ttk.Progressbar(self.progress_bar_frame, length=100, orient=tk.HORIZONTAL, mode='indeterminate')
                self.loading_progress.grid(row=0, column=0, padx=2, pady=2, sticky='news')
                self.loading_progress.start()
                print("creating indeterminate bar", self.loading_progress)

                this = self  # We set a variable to self in order to use it within TkinterProgress

                # Define an implementation of Progress that will update a ProgressBar widget
                class TkinterProgress(Progress):
                    def __init__(self, keys: int, exception: Exception = None):
                        try:
                            if this.loading_progress is not None:
                                this.loading_progress.stop()
                                this.loading_progress.destroy()
                                this.loading_progress = None
                        except TclError:
                            # We catch and ignore any TclErrors due to the multithreading madness going on
                            pass

                        if exception is None:
                            self.keys = keys
                            self.key = 0
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
                        self.key += n
                        this.progress_bar['value'] += (100 / self.keys) * n

                    def close(self):
                        # progress_bars[self.appid].destroy()
                        pass

                # Start the keychecker in a separate thread
                self.scrape_thread = threading.Thread(name='Scraper', target=lambda: keychecker(
                    self.save_filename,
                    BrowserTypes[self.browsers.get()],
                    keys,
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
        else:
            messagebox.showinfo('Textbox is empty', 'Textbox is empty')
