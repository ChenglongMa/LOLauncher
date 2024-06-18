import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import pystray
from PIL import Image
from watchdog.observers import Observer

from utils import *


class App:
    def __init__(self, setting_file, config, config_filename):
        self.setting_file = setting_file
        self.config = config
        self.config_filename = config_filename
        self.locale_dict = {value: key for key, value in LOCALE_CODES.items()}
        self.game_client = config.get("GameClient", "")
        self.observer = None

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.window_width = 300
        self.window_height = 330
        self.control_padding = 8
        self.layout_padding = 10

        self.stop_watching = tk.BooleanVar(value=False)
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.position_top = int(self.screen_height / 2 - self.window_height / 2)
        self.position_right = int(self.screen_width / 2 - self.window_width / 2)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{self.position_right}+{self.position_top}")
        self.root.iconbitmap('./assets/icon.ico')
        self.root.minsize(self.window_width, self.window_height)
        self.root.maxsize(self.window_width + 50, self.window_height + 50)
        # self.root.resizable(False, False)

        self.create_menu_bar()
        self.selected_locale = config.get("Locale", "zh_CN")
        self.create_locale_groupbox()
        self.create_quick_chat_groupbox()

        self.create_status_bar()
        self.create_launch_button()
        self.root.pack_propagate(True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)

    def run_tray_app(self):
        tray_app = pystray.Icon(APP_NAME, Image.open("./assets/tray_icon.png"), f"{APP_NAME} v{VERSION}",
                                menu=pystray.Menu(
                                    pystray.MenuItem("显示主窗口", self.on_window_restoring, default=True),
                                    pystray.MenuItem("帮助", self.show_about),
                                    pystray.MenuItem("退出", self.on_window_closing)
                                ))
        tray_app.run()

    def create_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="自动检测游戏配置文件", command=self.detect_metadata_file)
        self.file_menu.add_command(label="手动选择游戏配置文件", command=self.choose_metadata_file)
        # self.file_menu.add_command(label="恢复默认", command=self.reset_settings)
        self.menu_bar.add_cascade(label="文件", menu=self.file_menu)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="关于", command=self.show_about)
        self.help_menu.add_command(label="检查更新", command=lambda: check_for_updates(self.no_new_version_fn))
        self.menu_bar.add_cascade(label="帮助", menu=self.help_menu)
        self.root.config(menu=self.menu_bar)

    def create_locale_groupbox(self):
        self.locale_groupbox = tk.LabelFrame(self.root, text="语言设置")
        self.locale_var = tk.StringVar()
        self.locale_dropdown = ttk.Combobox(self.locale_groupbox, textvariable=self.locale_var, state="readonly")
        self.locale_dropdown['values'] = list(self.locale_dict.keys())
        self.locale_dropdown.current(list(self.locale_dict.values()).index(self.selected_locale))
        self.locale_dropdown.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.BOTH)
        self.locale_dropdown.bind("<<ComboboxSelected>>", self.on_dropdown_change)
        self.locale_groupbox.pack(fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

    def on_checkbox_change(self, *args):
        state = tk.NORMAL if self.quick_chat_enabled.get() else tk.DISABLED
        self.shortcut_entry.config(state=state)
        self.set_chat_button.config(state=state)

    def create_quick_chat_groupbox(self):
        self.quick_chat_groupbox = tk.LabelFrame(self.root, text="一键喊话设置")
        self.prompt_label = tk.Label(self.quick_chat_groupbox, text="该功能正在开发中，敬请期待！", foreground="red")
        self.prompt_label.pack(padx=self.layout_padding, pady=self.layout_padding, fill=tk.BOTH)

        self.quick_chat_enabled = tk.BooleanVar(value=False)
        self.quick_chat_enabled.trace("w", self.on_checkbox_change)
        state = tk.NORMAL if self.quick_chat_enabled.get() else tk.DISABLED
        self.quick_chat_checkbox = tk.Checkbutton(self.quick_chat_groupbox, text="一键喊话", variable=self.quick_chat_enabled, state=tk.DISABLED)
        self.quick_chat_checkbox.pack()

        self.shortcut_frame = tk.Frame(self.quick_chat_groupbox)

        self.shortcut_label = tk.Label(self.shortcut_frame, text="快捷键")
        self.shortcut_label.pack(side=tk.LEFT)
        self.shortcut_var = tk.StringVar()
        self.shortcut_entry = tk.Entry(self.shortcut_frame, state=state, textvariable=self.shortcut_var)
        self.shortcut_var.set("`")
        self.shortcut_entry.pack(side=tk.RIGHT)
        self.shortcut_frame.pack(padx=self.layout_padding)

        self.set_chat_button = tk.Button(self.quick_chat_groupbox, text="设置喊话内容", state=state)
        self.set_chat_button.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.BOTH)

        self.quick_chat_groupbox.pack(fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

    def create_launch_button(self):
        self.image = tk.PhotoImage(file="assets/button_icon.png")
        self.launch_button = tk.Button(self.root, text="英雄联盟，启动！", image=self.image, compound=tk.LEFT,
                                       command=self.start)
        self.launch_button.pack(side=tk.BOTTOM, pady=self.layout_padding)

    def create_status_bar(self):
        self.status_var = tk.StringVar(value="准备就绪")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.RIDGE, anchor=tk.W, foreground="gray")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message):
        self.status_var.set(message)

    def show_about(self, icon=None, item=None):
        if icon is not None:
            icon.stop()

        pady = self.layout_padding // 2
        self.about_window = tk.Toplevel(self.root)
        self.about_window.title("关于")
        self.about_window.iconbitmap('../icon.ico')
        self.about_window.geometry(f"+{self.position_right}+{self.position_top}")
        self.about_window.protocol("WM_DELETE_WINDOW", lambda: self.on_about_window_closing(create_tray=icon is not None))
        self.app_name_label = tk.Label(self.about_window, text=f"{APP_NAME} v{VERSION}")
        self.app_name_label.pack(padx=self.control_padding, pady=pady)

        self.author_label = tk.Label(self.about_window, text="作者：Chenglong Ma", fg="blue", cursor="hand2")
        self.author_label.pack(padx=self.control_padding, pady=pady)
        self.author_label.bind("<Button-1>", lambda event: open_my_homepage())

        self.homepage_label = tk.Label(self.about_window, text=f"GitHub：{REPO_NAME}", fg="blue", cursor="hand2")
        self.homepage_label.pack(padx=self.control_padding, pady=pady)
        self.homepage_label.bind("<Button-1>", lambda event: open_repo_page())

        self.copyright_label = tk.Label(self.about_window, text="Copyright © 2024 Chenglong Ma. All rights reserved.")
        self.copyright_label.pack(padx=self.control_padding, pady=pady)

    def on_about_window_closing(self, create_tray=False):
        self.about_window.destroy()
        if create_tray:
            self.run_tray_app()

    def no_new_version_fn(self):
        messagebox.showinfo("检查更新", "当前已是最新版本")
        self.update_status("当前已是最新版本")

    def reset_settings(self):
        print("Settings reset")

    def start_game(self, settings):
        self.update_status("正在启动游戏...")
        product_install_root = settings['product_install_root']

        product_install_root = product_install_root if os.path.exists(product_install_root) else "C:/"

        game_clients_in_settings = [os.path.join(product_install_root, "Riot Client/RiotClientServices.exe")]

        game_clients = filter_existing_files(to_list(self.game_client) + game_clients_in_settings)
        if not game_clients or len(game_clients) == 0:
            self.update_status("未找到 RiotClientServices.exe，请手动启动游戏。")
            return

        self.update_status("英雄联盟，启动！")
        self.game_client = os.path.normpath(game_clients[0])
        subprocess.run(['explorer.exe', self.game_client], check=False)

    def start(self):
        self.update_status("正在更新配置文件...")
        settings = update_settings(self.setting_file, self.selected_locale, msg_callback_fn=self.update_status)
        if not settings:
            messagebox.showerror("错误", "配置文件更新失败，无法启动游戏。")
            return
        watch_thread = threading.Thread(target=self.watch_file, daemon=True)
        watch_thread.start()
        self.start_game(settings)
        self.on_window_minimizing()

    def watch_file(self):
        event_handler = FileWatcher(self.setting_file, self.selected_locale, self.update_status)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=os.path.dirname(self.setting_file), recursive=False)
        self.observer.start()

        try:
            while not self.stop_watching.get():
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        except Exception as e:
            self.update_status(f"Error: {e}")
            self.observer.stop()
        self.observer.join()
        self.observer = None

    def detect_metadata_file(self):
        is_yes = tk.messagebox.askyesno("提示", "您确定要重新检测以修改已有配置？")
        if is_yes:
            setting_files = detect_metadata_file()
            if setting_files:
                self.setting_file = setting_files[0]  # TODO: multiple files support
                self.sync_config()
                msg = "游戏配置文件已更新"
            else:
                msg = "未找到有效配置，将继续使用之前的配置"
            self.update_status(msg)
            tk.messagebox.showinfo("提示", msg)

    def choose_metadata_file(self):
        is_yes = tk.messagebox.askyesno("提示", "已自动检测到游戏配置文件，您确定要手动选择吗？")
        if is_yes:
            selected_file = open_metadata_file_dialog(title="请选择 league_of_legends.live.product_settings.yaml 文件",
                                                      file_types=[('Riot 配置文件', '*.yaml'), ('所有文件', '*.*')],
                                                      initial_dir=DEFAULT_METADATA_DIR, initial_file=DEFAULT_METADATA_FILE)
            if selected_file:
                self.setting_file = selected_file
                self.sync_config()
                msg = "游戏配置文件已更新"
            else:
                msg = "未找到有效配置，将继续使用之前的配置"
            self.update_status(msg)
            tk.messagebox.showinfo("提示", msg)

    def on_dropdown_change(self, event):
        current_value = self.locale_var.get()
        self.selected_locale = self.locale_dict[current_value]
        self.update_status(f"语言将被设置为：{current_value}")

    def on_window_restoring(self, icon: pystray.Icon, item):
        icon.stop()
        self.root.after(0, self.root.deiconify)

    def on_window_minimizing(self, event=None):
        print("Minimizing...")
        self.sync_config()
        self.root.withdraw()
        self.run_tray_app()

    def run(self):
        self.root.mainloop()

    def sync_config(self):
        self.config = {
            "@注意": r"请使用\或/做为路径分隔符，如 C:\ProgramData 或 C:/ProgramData",
            "@SettingFile": "请在下方填写 league_of_legends.live.product_settings.yaml 文件路径",
            "SettingFile": self.setting_file,
            "@GameClient": "请在下方填写 RiotClientServices.exe 文件路径",
            "GameClient": self.game_client,
            "Locale": self.selected_locale,
            "QuickChatEnabled": self.quick_chat_enabled.get(),
            "Shortcut": self.shortcut_var.get(),
        }
        write_json(self.config_filename, self.config)
        print("Configuration file updated")
        return self.config

    def on_window_closing(self, icon: pystray.Icon, item):
        close = messagebox.askyesno("退出", "退出后再启动游戏时文本和语音将恢复为默认设置\n您确定要退出吗？")
        if close:
            icon.stop()
            if self.observer is not None:
                self.stop_watching.set(True)
                self.observer.stop()
            self.sync_config()
            self.root.destroy()
