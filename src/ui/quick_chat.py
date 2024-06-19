import os
import tkinter as tk

import keyboard

from assets import get_icon

import time
# import ctypes
# from ctypes import wintypes

from utils import COMMENT_PREFIX, go_to_previous_window, QUICK_CHAT_FILENAME, read_json, GUI_CONFIG_FILENAME

import pyautogui


def send_text_to_lol_chat(text):
    keyboard.send('alt+tab+tab')
    keyboard.send('enter')
    time.sleep(0.01)
    keyboard.write(text)
    keyboard.send('enter')


def send_text_to_lol_chat2(text):
    go_to_previous_window()

    pyautogui.press('enter')

    # Wait for the chat box to open
    time.sleep(0.1)

    # Type the text
    pyautogui.write(text)

    # Press enter to send the message
    pyautogui.press('enter')


#
# # 定义COPYDATASTRUCT结构体
# class COPYDATASTRUCT(ctypes.Structure):
#     _fields_ = [
#         ('dwData', wintypes.LPARAM),
#         ('cbData', wintypes.DWORD),
#         ('lpData', wintypes.LPVOID)
#     ]
#
#
# # 获取SendMessage函数并设置参数类型和返回类型
# SendMessage = ctypes.windll.user32.SendMessageW
# SendMessage.argtypes = wintypes.HWND, wintypes.UINT, wintypes.WPARAM, ctypes.POINTER(COPYDATASTRUCT)
# SendMessage.restype = wintypes.LRESULT
#
#
# # 定义sendMsg函数
# def sendMsg(hwnd, msg):
#     # 将消息转换为字节数组
#     msg = msg.encode('utf-8')
#     # 创建COPYDATASTRUCT实例
#     cds = COPYDATASTRUCT(0, len(msg), ctypes.cast(msg, ctypes.c_void_p))
#     # 调用SendMessage函数
#     SendMessage(hwnd, 0x004A, 0, ctypes.byref(cds))  # 0x004A is the Windows message code for WM_COPYDATA
#

class QuickChatModal:
    def __init__(self, root, config, gui_config):
        self.shortcut = None
        self.config = config
        self.root = root
        self.ui_config = gui_config

        self.chat_dialog = tk.Toplevel(self.root)
        self.chat_dialog.title("一键喊话")
        self.chat_dialog.withdraw()

        self.window_width = 350
        self.window_height = 400
        self.control_padding = 8
        self.layout_padding = 10

        self.screen_width = self.chat_dialog.winfo_screenwidth()
        self.screen_height = self.chat_dialog.winfo_screenheight()
        # print(self.chat_dialog.winfo_reqheight())
        self.position_top = self.ui_config.get('position_top', self.screen_height - self.window_height - 200)
        self.position_left = self.ui_config.get('position_left', 100)

        self.chat_dialog.geometry(f"{self.window_width}x{self.window_height}+{self.position_left}+{self.position_top}")
        self.chat_dialog.iconbitmap(get_icon('icon.ico'))
        self.chat_listbox = self.create_listbox()

        self.chat_dialog.attributes('-topmost', True)

        # Hide the top level window initially
        self.chat_dialog.withdraw()
        self.chat_dialog.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)
        self.chat_dialog.bind('<B1-Motion>', self.dragwin)

    def create_listbox(self):
        list_box = tk.Listbox(self.chat_dialog, selectmode=tk.SINGLE, height=30, font=("Helvetica", 16))
        list_box.pack(fill=tk.BOTH, expand=True)
        # list_box.bind("<Double-Button-1>", lambda event: send_text_to_lol_chat(list_box.get(list_box.curselection())))
        # list_box.bind("<Return>", lambda event: send_text_to_lol_chat(list_box.get(list_box.curselection())))
        # list_box.bind("<Double-Button-1>", self.on_chat_text_selected)
        list_box.bind("<<ListboxSelect>>", self.on_chat_text_selected)
        return list_box

    def on_chat_text_selected(self, event):
        widget = event.widget
        selection = widget.curselection()
        value = widget.get(selection[0])
        send_text_to_lol_chat(value)

    def dragwin(self, event):
        x = self.chat_dialog.winfo_pointerx() - self.chat_dialog.winfo_vrootx()
        y = self.chat_dialog.winfo_pointery() - self.chat_dialog.winfo_vrooty()
        self.chat_dialog.geometry(f"+{x}+{y}")
        self.ui_config['position_top'] = y
        self.ui_config['position_left'] = x

    def set_hotkey(self, shortcut):
        if not shortcut:
            return
        if self.shortcut:
            keyboard.remove_hotkey(self.shortcut)
        self.shortcut = shortcut
        keyboard.add_hotkey(self.shortcut, self.toggle_window)

    def refresh_chat_list(self):
        if os.path.exists(QUICK_CHAT_FILENAME):
            self.chat_listbox.delete(0, tk.END)
            with open(QUICK_CHAT_FILENAME, 'r', encoding='utf-8') as file:
                for line in file:
                    line = line.strip()
                    if not line.startswith(COMMENT_PREFIX) and line:
                        self.chat_listbox.insert(tk.END, line)

    def toggle_window(self):
        if self.chat_dialog.winfo_viewable():
            self.chat_dialog.withdraw()

        else:
            self.chat_dialog.deiconify()
            self.refresh_chat_list()

    def on_window_minimizing(self):
        self.chat_dialog.withdraw()

    def close(self):
        if self.shortcut:
            keyboard.remove_hotkey(self.shortcut)
        self.chat_dialog.destroy()
