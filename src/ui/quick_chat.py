import os
import threading
import tkinter as tk

import keyboard

from assets import get_asset
from core.platform import is_running
from core.quick_chat import create_quick_chat_file, read_quick_chat_file, send_text_to_lol_chat
from ui.utils import reset_list_box_colors


class QuickChatDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.hotkey = None
        self.shortcut = None
        self.lol_pid = None
        self.lock = threading.Lock()
        self.drag_origin = None

        # UI setup
        self.default_bg = "#264C47"
        self.default_fg = "#8F7A48"
        self.border_color = "#927934"
        self.border_color_inactive = "#463714"
        self.hover_bg = "#C89B3C"
        self.hover_fg = "#010A13"
        self.withdraw()
        self.title("一键喊话")
        self.iconbitmap(get_asset('icon.ico'))
        self.chat_listbox = self.create_listbox(self)
        self.attributes('-topmost', True)
        self.attributes('-alpha', 0.95)
        self.config(
            background=self.default_bg,
            highlightthickness=3,
            highlightcolor=self.border_color,
            highlightbackground=self.border_color_inactive,
            cursor='fleur',
        )
        self.init_geometry()

        self.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<ButtonRelease-1>", self.stop_move)
        self.bind("<B1-Motion>", self.do_move)

        self.bind('<Configure>', self.on_resize)

    def on_resize(self, event):
        if event.widget is self:
            self.app.ui_config.update(
                QuickChatWidth=self.winfo_width(),
                QuickChatHeight=self.winfo_height(),
                QuickChatX=self.winfo_x(),
                QuickChatY=self.winfo_y(),
            )

    def init_geometry(self):
        config = self.app.ui_config
        width = max(config.get("QuickChatWidth", 300), 300)
        height = max(config.get("QuickChatHeight", 220), 120)
        screen_height = self.winfo_screenheight()
        position_top = config.get("QuickChatY", screen_height - height - 500)
        position_top = max(0, min(position_top, screen_height - height))
        position_left = max(config.get("QuickChatX", 100), 0)
        self.geometry(f"{width}x{height}+{position_left}+{position_top}")
        self.minsize(300, 120)

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
        reset_list_box_colors(list_box, self.default_bg, self.default_fg)
        if 0 <= index < list_box.size():
            list_box.config(cursor='hand2')
            list_box.itemconfig(index, {'bg': self.hover_bg, 'fg': self.hover_fg})
        else:
            list_box.config(cursor='arrow')

    def on_mouse_leave(self, event):
        list_box = event.widget
        reset_list_box_colors(list_box, self.default_bg, self.default_fg)

    def on_chat_text_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        if not selection:
            return
        self.withdraw()
        if not self.lol_pid:
            return
        selected_chat = widget.get(selection[0])

        thread = threading.Thread(target=send_text_to_lol_chat, args=(selected_chat, self.lock, self.lol_pid), daemon=True)
        thread.start()

    def disable_hotkey(self):
        if self.hotkey is not None:
            keyboard.remove_hotkey(self.hotkey)
            self.hotkey = None
            self.shortcut = None

    def set_hotkey(self, shortcut):
        if not shortcut or shortcut == self.shortcut:
            return
        self.disable_hotkey()
        self.hotkey = keyboard.add_hotkey(shortcut, lambda: self.app.post_to_ui(self.toggle_window))
        self.shortcut = shortcut

    def toggle_window(self):
        if not self.app.quick_chat_enabled:
            return
        if self.winfo_viewable():
            self.withdraw()
            return
        self.lol_pid = is_running(self.app.config.get("Process Name", "League of Legends.exe"))
        if not self.lol_pid:
            decision = self.app.dialog.choose(
                "提示", "游戏对局未开始，是否显示一键喊话对话框？", ["是", "取消", "关闭一键喊话"],
            )
            if decision == "关闭一键喊话":
                self.app.set_quick_chat_enabled(False)
                return
            if decision != "是":
                return
        self.refresh_chat_list()
        self.deiconify()
        self.lift()

    def refresh_chat_list(self):
        path = self.app.quick_chat_filename
        if not os.path.exists(path):
            create_quick_chat_file(self.app.config_filename)
        self.chat_listbox.delete(0, tk.END)
        self.chat_listbox.insert(tk.END, *read_quick_chat_file(path))

    def do_move(self, event):
        if self.drag_origin is not None:
            x, y = self.drag_origin
            self.geometry(f"+{event.x_root - x}+{event.y_root - y}")

    def start_move(self, event):
        self.drag_origin = event.x_root - self.winfo_x(), event.y_root - self.winfo_y()

    def stop_move(self, event):
        self.drag_origin = None

    def on_window_minimizing(self):
        self.withdraw()
