import tkinter as tk


class GrantPackage(tk.Frame):
    def __init__(self, master):
        print('Keychecker page')
        tk.Frame.__init__(self, master=master, width=800, height=300)
