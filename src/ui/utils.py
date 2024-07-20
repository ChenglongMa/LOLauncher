import subprocess
import tkinter as tk

from assets import get_asset
from utils import open_web

THEME_COLOR = {
    "dark": {
        "warning_bg": "#333333",
        "warning_fg": "white",
        "border": "#927934",
        "border_inactive": "#463714",
        "hover_bg": "#C89B3C",
        "hover_fg": "#010A13",
        "accent": "#C89B3C",
    },
    "light": {
        "warning_bg": "#F0E6D2",
        "warning_fg": "#010A13",
        "border": "#927934",
        "border_inactive": "#463714",
        "hover_bg": "#C89B3C",
        "hover_fg": "#010A13",
        "accent": "blue",
    }
}


def reset_list_box_colors(list_box, default_bg, default_fg):
    for i in range(list_box.size()):
        list_box.itemconfig(i, {'bg': default_bg, 'fg': default_fg})


def open_asset(uri):
    if uri.startswith("http"):
        open_web(uri)
        return
    file_path = get_asset(uri)
    subprocess.run(['start', file_path], shell=True, check=False)


def create_warning_label(parent, normal_text, link_text, uri, theme="dark"):
    label = tk.Text(parent, height=1, background=THEME_COLOR[theme]["warning_bg"], foreground=THEME_COLOR[theme]["warning_fg"], relief=tk.SOLID,
                    borderwidth=1)
    label.insert(1.0, normal_text + " ", tk.CENTER)
    label.insert(tk.END, link_text, "link")
    label.tag_config("link", foreground=THEME_COLOR[theme]["accent"], underline=True)
    label.tag_bind("link", "<Button-1>", lambda e: open_asset(uri))
    label.tag_bind("link", "<Enter>", lambda e: label.config(cursor="hand2"))
    label.tag_bind("link", "<Leave>", lambda e: label.config(cursor=""))
    label.tag_config(tk.CENTER, justify=tk.CENTER)
    label.configure(state=tk.DISABLED)  # make it uneditable
    return label
