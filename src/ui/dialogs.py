import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText


class ChoiceDialog(simpledialog.Dialog):
    def __init__(self, parent, title, message, choices, details=""):
        self.message = message
        self.choices = choices
        self.details = details
        super().__init__(parent, title)

    def body(self, frame):
        ttk.Label(frame, text=self.message, wraplength=440, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 8))
        if self.details:
            notes = ScrolledText(frame, width=58, height=9, wrap=tk.WORD, font="TkDefaultFont")
            notes.insert("1.0", self.details)
            notes.configure(state=tk.DISABLED)
            notes.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.options = tk.Listbox(frame, height=min(8, len(self.choices)), width=58, exportselection=False)
        self.options.insert(tk.END, *self.choices)
        self.options.selection_set(0)
        self.options.bind("<Double-Button-1>", self.ok)
        scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=self.options.xview)
        self.options.configure(xscrollcommand=scrollbar.set)
        self.options.pack(fill=tk.BOTH, expand=True)
        scrollbar.pack(fill=tk.X)
        return self.options

    def buttonbox(self):
        buttons = ttk.Frame(self, padding=8)
        ttk.Button(buttons, text="确定", command=self.ok).pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="取消", command=self.cancel).pack(side=tk.LEFT, padx=4)
        buttons.pack()
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        return bool(self.options.curselection())

    def apply(self):
        self.result = self.options.get(self.options.curselection()[0])


class TkDialogService:
    def __init__(self, parent: tk.Tk):
        self.parent = parent

    def confirm(self, title, message):
        return messagebox.askyesno(title, message, parent=self.parent, default=messagebox.NO)

    def choose(self, title, message, choices, *, details=""):
        if choices:
            return ChoiceDialog(self.parent, title, message, choices, details).result
        return None

    def input_text(self, title, message, default=""):
        return simpledialog.askstring(title, message, parent=self.parent, initialvalue=default)

    def select_file(self, title, file_types, initial_dir="", initial_file=""):
        return filedialog.askopenfilename(
            parent=self.parent, title=title, filetypes=file_types,
            initialdir=os.path.normpath(initial_dir) if initial_dir else "",
            initialfile=initial_file,
        ) or None

    def info(self, title, message):
        messagebox.showinfo(title, message, parent=self.parent)

    def error(self, title, message):
        messagebox.showerror(title, message, parent=self.parent)
