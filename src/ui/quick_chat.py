import os
import threading
import time
import tkinter as tk
from tkinter import ttk

import easygui
import keyboard

from assets import get_asset
from ui.utils import reset_list_box_colors
from utils import is_foreground_window, bring_to_foreground, is_running, QUICK_CHAT_FILENAME, COMMENT_PREFIX, send_text


def send_text_to_lol_chat(text, lock, pid=None):
    with lock:
        if not pid:
            print("No pid provided, program is not running.")
            return
        is_foreground = False
        for _ in range(5):
            is_foreground = is_foreground_window(pid)
            if is_foreground:
                break
            bring_to_foreground(pid)
            time.sleep(0.1)

        if not is_foreground:
            print("Program is not in foreground.")
            return

        print(f"Sending text to pid {pid}")
        send_text(text)


class QuickChatDialog(tk.Toplevel):
    def __init__(self, app, config, gui_config):
        self.parent_view = app.root
        super().__init__(self.parent_view)
        # Config
        self.app = app
        self.user_config = config
        self.ui_config = gui_config
        self.shortcut = None
        self.lol_pid = None
        self.lock = threading.Lock()

        # UI setup
        self.default_bg = "#264C47"
        self.default_fg = "#8F7A48"
        self.border_color = "#927934"
        self.border_color_inactive = "#463714"
        self.hover_bg = "#C89B3C"
        self.hover_fg = "#010A13"
        # self.hover_fg = "#F0E6D2"
        self.withdraw()  # Hide the window initially
        self.title("一键喊话")
        self.iconbitmap(get_asset('icon.ico'))
        self.chat_listbox = self.create_listbox(self)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.95)
        self.config(
            background=self.default_bg,
            # borderwidth=10, # DON'T use this to change border width
            highlightthickness=3,
            highlightcolor=self.border_color,
            highlightbackground=self.border_color_inactive,
            cursor='fleur',
        )
        # self.overrideredirect(True)
        self.init_geometry()

        self.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<B1-Motion>", self.do_move)

        self.bind('<Configure>', self.on_resize)

    def on_resize(self, event):
        self.ui_config['QuickChatWidth'] = self.winfo_width()
        self.ui_config['QuickChatHeight'] = self.winfo_height()
        self.ui_config['QuickChatX'] = self.winfo_x()
        self.ui_config['QuickChatY'] = self.winfo_y()

    def init_geometry(self):
        width = self.ui_config.get('QuickChatWidth', 300)
        width = max(width, 300)
        height = self.ui_config.get('QuickChatHeight', self.chat_listbox.winfo_reqheight())
        height = max(height, self.chat_listbox.winfo_reqheight())
        # screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        position_top = self.ui_config.get('QuickChatY', screen_height - height - 500)
        position_top = max(0, min(position_top, screen_height - height))
        position_left = self.ui_config.get('QuickChatX', 100)
        position_left = max(0, position_left)
        self.geometry(f"{width}x{height}+{position_left}+{position_top}")
        self.minsize(300, self.chat_listbox.winfo_reqheight())

    def create_listbox(self, parent):
        # NOTE: set exportselection=False to prevent the listbox from triggering the on_chat_text_selected event
        list_box = tk.Listbox(
            parent,
            selectmode=tk.SINGLE,
            font=("Helvetica", 16),
            exportselection=False,
            bg=self.default_bg, fg=self.default_fg,
            highlightthickness=0,
            borderwidth=0,
        )
        list_box.pack(expand=True, fill=tk.BOTH, padx=2, pady=4, anchor=tk.NW)
        list_box.bind("<<ListboxSelect>>", self.on_chat_text_selected)

        list_box.bind("<Motion>", self.on_mouse_move)
        list_box.bind("<Leave>", self.on_mouse_leave)

        return list_box

    def on_mouse_move(self, event):
        list_box = event.widget
        index = list_box.nearest(event.y)
        if 0 <= index < list_box.size():
            list_box.config(cursor='hand2')
        else:
            list_box.config(cursor='arrow')
        reset_list_box_colors(list_box, self.default_bg, self.default_fg)
        list_box.itemconfig(index, {'bg': self.hover_bg, 'fg': self.hover_fg})

    def on_mouse_leave(self, event):
        list_box = event.widget
        reset_list_box_colors(list_box, self.default_bg, self.default_fg)

    def on_chat_text_selected(self, event=None):
        self.withdraw()
        if not self.lol_pid:
            print("League of Legends is not running.")
            return
        widget = event.widget  # i.e., listbox
        selection = widget.curselection()
        if not selection:
            print("No selection.")
            return
        selected_chat = widget.get(selection[0])

        thread = threading.Thread(target=send_text_to_lol_chat, args=(selected_chat, self.lock, self.lol_pid))
        thread.start()

    def disable_hotkey(self):
        if self.shortcut:
            keyboard.remove_hotkey(self.shortcut)
            self.shortcut = None

    def set_hotkey(self, shortcut):
        if not shortcut or shortcut == self.shortcut:
            return
        if self.shortcut:
            keyboard.remove_hotkey(self.shortcut)
        self.shortcut = shortcut
        keyboard.add_hotkey(self.shortcut, self.toggle_window)

    def toggle_window(self):
        if self.winfo_viewable():
            self.withdraw()
        else:
            self.lol_pid = is_running(self.user_config.get("Process Name", "League of Legends.exe"))
            if not self.lol_pid:
                decision = easygui.buttonbox("游戏对局未开始，是否显示一键喊话对话框？", "提示", ["是", "取消", "关闭一键喊话"])
                if not decision or decision == "取消":
                    return
                elif decision == "关闭一键喊话":
                    self.app.quick_chat_enabled.set(False)
                    self.disable_hotkey()
                    return
            self.deiconify()
            self.refresh_chat_list()

    def refresh_chat_list(self):
        if os.path.exists(QUICK_CHAT_FILENAME):
            self.chat_listbox.delete(0, tk.END)
            with open(QUICK_CHAT_FILENAME, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line.startswith(COMMENT_PREFIX) and line:
                        self.chat_listbox.insert(tk.END, line)
            listbox_height = self.chat_listbox.size()
            self.chat_listbox.config(height=listbox_height)

    def do_move(self, event):
        dx = event.x - self.x
        dy = event.y - self.y
        x = self.winfo_x() + dx
        y = self.winfo_y() + dy
        self.geometry(f"+{x}+{y}")

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        self.x = None
        self.y = None

    def on_window_minimizing(self):
        self.withdraw()
