import tkinter as tk

# https://stackoverflow.com/questions/27820178/how-to-add-placeholder-to-an-entry-in-tkinter/47928390
class TextPlaceholder(tk.Text):
    """
    Text widget with a placeholder
    """

    def __init__(self, master=None, placeholder="", color='grey'):
        super().__init__(master)

        self.placeholder = placeholder
        self.placeholder_color = color
        self.default_fg_color = self['fg']

        self.bind("<FocusIn>", self.foc_in)
        self.bind("<FocusOut>", self.foc_out)

        self.put_placeholder()

    def put_placeholder(self):
        self.insert(1.0, self.placeholder)
        self['fg'] = self.placeholder_color

    def foc_in(self, *args):
        if self['fg'] == self.placeholder_color:
            self.delete(1.0, tk.END)
            self['fg'] = self.default_fg_color

    def foc_out(self, *args):
        if not self.get(1.0):
            self.put_placeholder()
