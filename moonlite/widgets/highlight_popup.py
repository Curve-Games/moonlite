import tkinter as tk


class HighlightPopup(tk.Text):
    """tk.Text widget with a highlight that will initiate a popup callback after a certain waittime"""
    def __init__(self, master=None, showtip=lambda event: None, waittime: int = 500):
        super().__init__(master)
        self.waittime = waittime
        self.showtip = showtip
        self.id = None
        self.tw = None

        self.bind('<ButtonPress-1>', self._on_click)
        self.tag_remove('highlight', '1.0', 'end')
        self.tag_configure("highlight", background="green", foreground="black")

    def get_highlighted(self):
        return self.get(*self.tag_ranges('highlight'))

    def _on_click(self, event=None):
        self.tag_remove("highlight", "1.0", "end")
        self.tag_add("highlight", "insert wordstart", "insert wordend")
        self.tag_bind("highlight", "<Enter>", self._enter)
        self.tag_bind('highlight', '<Leave>', self._leave)

    def _enter(self, event=None):
        self._schedule(event)

    def _leave(self, event=None):
        self._unschedule()
        self._hidetip()

    def _schedule(self, event=None):
        self._unschedule()
        self.id = self.after(self.waittime, lambda: self.showtip(event))

    def _unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.after_cancel(id)

    def _hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
