import subprocess
import tkinter as tk

from assets import get_asset
from utils import open_web


def reset_list_box_colors(list_box, default_bg, default_fg):
    for i in range(list_box.size()):
        list_box.itemconfig(i, {'bg': default_bg, 'fg': default_fg})


def open_asset(uri):
    if uri.startswith("http"):
        open_web(uri)
        return
    file_path = get_asset(uri)
    subprocess.run(['start', file_path], shell=True, check=False)


def create_warning_label(parent, normal_text, link_text, uri):
    label = tk.Text(parent, height=1, background="#ffffe0", relief=tk.SOLID, borderwidth=1)
    label.insert(1.0, normal_text + " ", tk.CENTER)
    label.insert(tk.END, link_text, "link")
    label.tag_config("link", foreground="blue", underline=True)
    label.tag_bind("link", "<Button-1>", lambda e: open_asset(uri))
    label.tag_bind("link", "<Enter>", lambda e: label.config(cursor="hand2"))
    label.tag_bind("link", "<Leave>", lambda e: label.config(cursor=""))
    label.tag_config(tk.CENTER, justify=tk.CENTER)
    label.configure(state=tk.DISABLED)  # make it uneditable
    return label
