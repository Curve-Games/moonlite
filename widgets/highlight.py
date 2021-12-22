import tkinter as tk


class Highlight(tk.Text):
    def __init__(self, master=None, callback=lambda event: None):
        super().__init__(master)

        self.callback = callback
        self.bind("<ButtonRelease-1>", self._on_click)
        self.tag_remove('highlight', '1.0', 'end')
        self.tag_configure("highlight", background="green", foreground="black")

    def _on_click(self, event):
        self.tag_remove("highlight", "1.0", "end")
        self.tag_add("highlight", "insert wordstart", "insert wordend")
        self.tag_bind("highlight", "<Button-1>", self.callback)
