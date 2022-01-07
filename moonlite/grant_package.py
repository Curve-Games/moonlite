import io
import os
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, ttk

import requests
from PIL import Image, ImageTk

from moonlite.widgets.highlight_popup import HighlightPopup
from moonlite.widgets.text_placeholder import TextPlaceholder
from moonlite.widgets.tool_frame import ToolFrame


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

        self.entry = HighlightPopup(self.bottom_frame, lambda event: self._popup_package_details(event))
        self.entry.grid(row=0, column=0, padx=2, pady=2, sticky='news')
        scrollbar = tk.Scrollbar(self.entry)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar.config(command=self.entry.yview)
        self.entry.config(yscrollcommand=scrollbar.set)

    def _popup_package_details(self, event):
        # Create a top level widget at the event x_root, y_root
        self.entry.tw = tk.Toplevel(self.entry)
        self.entry.tw.columnconfigure(0, weight=1, minsize=200)
        self.entry.tw.rowconfigure(0, weight=1, minsize=100)
        self.entry.tw.wm_overrideredirect(True)
        self.entry.tw.wm_geometry("200x100+{0}+{1}".format(event.x_root - 100, event.y_root - 100))

        print('highlighted is:', self.entry.get_highlighted())
        self.entry.frame = tk.Frame(self.entry.tw)
        self.entry.frame.grid(row=0, column=0, padx=2, pady=2, sticky='news')
        highlighted = self.entry.get_highlighted()

        def fetch_profile(entry):
            def create_frame():
                entry.frame.destroy()
                entry.frame = tk.Frame(entry.tw)
                entry.frame.grid(row=0, column=0, padx=2, pady=2, sticky='news')

            def single_grid():
                entry.frame.columnconfigure(0, weight=1, minsize=200)
                entry.frame.rowconfigure(0, weight=1, minsize=100)

            try:
                if highlighted and highlighted.isnumeric() and 17 <= len(highlighted) <= 20:
                    print(f'\"{highlighted}\" is formatted as a STEAMID64')
                    profile_summary = requests.get(
                        f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/'
                        f'?key=0C17FA31D5AA91340F1BC3D991F3E382&steamids={highlighted}'
                    ).json().get('response', {}).get('players', [{}])[0]
                    personaname = profile_summary['personaname']
                    avatar = profile_summary['avatarmedium']
                    print('avatar url', avatar)
                    response = requests.get(avatar, stream=True)
                    image = ImageTk.PhotoImage(Image.open(io.BytesIO(response.raw.read())))
                    create_frame()
                    entry.frame.columnconfigure(0, weight=1, minsize=200)
                    entry.frame.rowconfigure(0, weight=1, minsize=75)
                    entry.frame.rowconfigure(1, weight=1, minsize=25)

                    entry.photo = tk.Label(entry.frame, image=image)
                    entry.photo.grid(row=0, column=0, padx=2, pady=2, sticky='news')
                    entry.name = tk.Label(entry.frame, text=personaname)
                    entry.name.grid(row=1, column=0, padx=2, pady=2, sticky='news')
                else:
                    error = f'{highlighted.encode("unicode_escape")} is not formatted as a STEAMID64'
                    print(error)
                    create_frame()
                    single_grid()
                    tk.Label(entry.frame, text=error, wraplength=180).grid(row=0, column=0, padx=2, pady=2, sticky='news')
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)
                create_frame()
                single_grid()
                tk.Label(entry.frame, text=f'\"{e}\" occurred whilst fetching profile', wraplength=180).grid(row=0, column=0, padx=2, pady=2, sticky='news')

        profile_fetch = threading.Thread(name=f'Profile fetch for {highlighted}', target=lambda: fetch_profile(self.entry))
        profile_fetch.start()
        # progress_frame.columnconfigure()
        # progress_frame.rowconfigure()

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
