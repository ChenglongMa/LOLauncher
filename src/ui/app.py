import threading
import tkinter as tk
from tkinter import ttk, messagebox, font
import sv_ttk

import pystray
from PIL import Image
from watchdog.observers import Observer

from assets import get_asset
from ui.quick_chat import QuickChatDialog
from ui.utils import create_warning_label, THEME_COLOR
from utils import *


def change_font(font_family):
    for font_name in font.names():
        _font = font.nametofont(font_name)
        _font.config(family=font_family)


class App:
    def __init__(self, setting_files, config, gui_config):
        self.setting_files: [str] = setting_files
        self.config = config
        self.ui_config = gui_config
        self.locale_dict = {value: key for key, value in LOCALE_CODES.items()}
        self.game_client = config.get("GameClient", "")
        self.observers: [Observer] = []

        self.root = tk.Tk()
        self.theme: str = self.ui_config.get("Theme", "light")
        if "dark" in self.theme.lower():
            sv_ttk.use_dark_theme()
        else:
            sv_ttk.use_light_theme()
        change_font("Microsoft YaHei UI")
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.window_width = 350
        self.window_height = 420
        self.control_padding = 10
        self.layout_padding = 15

        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.position_top = int(self.screen_height / 2 - self.window_height / 2)
        self.position_right = int(self.screen_width / 2 - self.window_width / 2)
        self.root.geometry(f"{self.window_width}x{self.window_height}+{self.position_right}+{self.position_top}")
        self.root.iconbitmap(get_asset('icon.ico'))
        self.root.minsize(self.window_width, self.window_height)
        self.root.maxsize(self.window_width + 50, self.window_height + 50)
        # self.root.resizable(False, False)

        self.create_menu_bar()
        self.selected_locale = config.get("Locale", "zh_CN")
        if self.selected_locale not in LOCALE_CODES.keys():
            self.selected_locale = "zh_CN"
        self.create_locale_groupbox()
        self.create_quick_chat_groupbox()

        self.create_status_bar()
        self.create_launch_button()
        self.tray_app = self.create_tray_app()
        self.tray_thread = threading.Thread(target=self.tray_app.run)

        self.root.pack_propagate(True)

        self.root.protocol("WM_DELETE_WINDOW", self.on_window_minimizing)

    def create_tray_app(self):
        return pystray.Icon(
            APP_NAME,
            Image.open(get_asset("tray_icon.png")),
            f"{APP_NAME} v{VERSION}",
            menu=self.create_tray_menu()
        )

    def create_tray_menu(self):
        return pystray.Menu(
            pystray.MenuItem("显示主窗口", self.on_window_restoring, default=True),
            pystray.MenuItem("一键喊话", self.set_quick_chat, checked=lambda item: self.quick_chat_enabled_setting),
            pystray.MenuItem("帮助", self.show_about),
            pystray.MenuItem("退出", self.on_window_closing)
        )

    def set_quick_chat(self, icon, item):
        print("Quick chat enabled:", item.checked)
        current_state = self.quick_chat_enabled.get()
        self.quick_chat_enabled.set(not current_state)
        self.quick_chat_enabled_setting = not current_state

    def set_process_name(self):
        process_name = easygui.enterbox("请输入进程名称", "设置进程名称", self.config.get("Process Name", "League of Legends.exe"))
        if process_name:
            self.config["Process Name"] = process_name
            self.sync_config()
            self.update_status(f"进程名称已设置为：{process_name}")

    def create_menu_bar(self):
        self.menu_bar = tk.Menu(self.root)
        self.setting_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.setting_menu.add_command(label="自动检测游戏配置文件", command=self.detect_metadata_file)
        self.setting_menu.add_command(label="手动选择游戏配置文件", command=self.choose_metadata_file)
        self.setting_menu.add_command(label="设置进程名称", command=self.set_process_name)
        self.setting_menu.add_separator()
        self.setting_menu.add_command(label="切换颜色主题", command=lambda: self.root.after(0, self.toggle_theme))
        self.minimize_on_closing = tk.BooleanVar(value=self.config.get("MinimizeOnClosing", True))
        self.setting_menu.add_checkbutton(label="关闭时最小化到托盘", variable=self.minimize_on_closing)
        self.menu_bar.add_cascade(label="设置", menu=self.setting_menu)
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="关于", command=self.show_about)
        self.help_menu.add_command(label="检查更新", command=lambda: check_for_updates(self.no_new_version_fn))
        self.menu_bar.add_cascade(label="帮助", menu=self.help_menu)
        self.root.config(menu=self.menu_bar)

    def toggle_theme(self):
        sv_ttk.toggle_theme()
        self.theme = sv_ttk.get_theme()
        self.quick_chat_warning_label.config(background=THEME_COLOR[self.theme]["warning_bg"], foreground=THEME_COLOR[self.theme]["warning_fg"])
        self.quick_chat_warning_label.tag_config("link", foreground=THEME_COLOR[self.theme]["accent"], underline=True)
        self.create_custom_button_style()

    def create_locale_groupbox(self):
        self.locale_groupbox = ttk.LabelFrame(self.root, text="语言设置", style='Card.TFrame')
        self.locale_var = tk.StringVar(value=LOCALE_CODES[self.selected_locale])
        self.locale_dropdown = ttk.Combobox(self.locale_groupbox, textvariable=self.locale_var, state="readonly", exportselection=True)
        self.locale_dropdown['values'] = list(self.locale_dict.keys())
        self.locale_dropdown.current(list(self.locale_dict.values()).index(self.selected_locale))
        self.locale_dropdown.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.BOTH)
        self.locale_dropdown.bind("<<ComboboxSelected>>", self.on_locale_changed)
        self.locale_groupbox.pack(fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

    def on_quick_chat_enable_change(self, *args):
        if not self.config.get("QuickChatNoteNotAsk", False) and self.quick_chat_enabled.get():
            decision = easygui.buttonbox('您是否已根据《注意事项》设置好"无边框"模式？',
                                         "启用前的准备", ["已设置好", "还没有", "已设置好，不要再提醒"])
            if not decision or decision == "还没有":
                self.quick_chat_enabled.set(False)
                self.quick_chat_enabled_setting = False
                self.tray_app.update_menu()
                return
            elif decision == "已设置好，不要再提醒":
                self.config["QuickChatNoteNotAsk"] = True

        state = tk.NORMAL if self.quick_chat_enabled.get() else tk.DISABLED
        self.shortcut_dropdown.config(state=state)
        self.set_chat_button.config(state=state)
        self.quick_chat_enabled_setting = self.quick_chat_enabled.get()
        self.tray_app.update_menu()
        if self.quick_chat_enabled_setting:
            self.update_status("一键喊话已启用")
            create_quick_chat_file(CONFIG_FILENAME)
            self.quick_chat_dialog.set_hotkey(self.shortcut_var.get())
        else:
            self.update_status("一键喊话已禁用")
            self.quick_chat_dialog.disable_hotkey()

    def create_quick_chat_groupbox(self):
        self.quick_chat_groupbox = ttk.LabelFrame(self.root, text="一键喊话设置", style='Card.TFrame')
        self.quick_chat_doc = self.config.get("QuickChatDoc", QUICK_CHAT_DOC)
        self.quick_chat_warning_label = create_warning_label(
            self.quick_chat_groupbox,
            "\u26A1 使用前请仔细阅读", "注意事项",
            self.quick_chat_doc,
            theme=self.theme
        )
        self.quick_chat_warning_label.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.BOTH)
        self.quick_chat_enabled_setting = self.config.get("QuickChatEnabled", False)
        self.quick_chat_enabled = tk.BooleanVar(value=self.quick_chat_enabled_setting)
        self.quick_chat_enabled.trace("w", self.on_quick_chat_enable_change)

        self.quick_chat_checkbox = ttk.Checkbutton(self.quick_chat_groupbox, text="一键喊话", variable=self.quick_chat_enabled,
                                                   style='Switch.TCheckbutton')
        self.quick_chat_checkbox.pack()

        self.shortcut_frame = ttk.Frame(self.quick_chat_groupbox)

        self.shortcut_label = ttk.Label(self.shortcut_frame, text="快捷键")
        self.shortcut_label.pack(side=tk.LEFT, padx=self.control_padding)
        available_shortcuts = ["`", "Alt", "Ctrl", "Shift", "Tab"]
        setting_value = self.config.get("QuickChatShortcut", "`")
        if setting_value not in available_shortcuts:
            available_shortcuts.append(setting_value)
        self.shortcut_var = tk.StringVar(value=setting_value)

        state = "readonly" if self.quick_chat_enabled.get() else tk.DISABLED
        self.shortcut_dropdown = ttk.Combobox(self.shortcut_frame, state=state, textvariable=self.shortcut_var, exportselection=True)

        self.shortcut_dropdown['values'] = available_shortcuts
        self.shortcut_dropdown.current(available_shortcuts.index(self.shortcut_var.get()))
        self.shortcut_dropdown.bind("<<ComboboxSelected>>", self.on_shortcut_changed)
        self.shortcut_dropdown.pack(side=tk.RIGHT)

        self.shortcut_frame.pack(padx=self.layout_padding)

        state = tk.NORMAL if self.quick_chat_enabled.get() else tk.DISABLED
        self.set_chat_button = ttk.Button(self.quick_chat_groupbox, text="设置喊话内容", state=state, command=self.open_quick_chat_file)
        self.set_chat_button.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.BOTH)

        self.quick_chat_groupbox.pack(fill=tk.BOTH, padx=self.layout_padding, pady=self.layout_padding)

        self.quick_chat_dialog = QuickChatDialog(self, self.config, self.ui_config)
        if self.quick_chat_enabled_setting:
            self.quick_chat_dialog.set_hotkey(self.config.get('QuickChatShortcut', '`'))
        else:
            self.quick_chat_dialog.disable_hotkey()

    def open_quick_chat_file(self):
        print("Opening quick chat file...")
        if not os.path.exists(QUICK_CHAT_FILENAME):
            create_quick_chat_file(CONFIG_FILENAME)
        subprocess.run(['notepad.exe', QUICK_CHAT_FILENAME], check=False)

    def create_custom_button_style(self):
        style = ttk.Style()
        style.configure('CustomAccent.TButton', font=('Microsoft YaHei', 16, 'bold'))

    def create_launch_button(self):
        self.create_custom_button_style()
        self.image = tk.PhotoImage(file=get_asset("button_icon.png"))
        self.launch_button = ttk.Button(self.root, text="英雄联盟，启动！", image=self.image, compound=tk.LEFT,
                                        command=self.start, style="CustomAccent.TButton")
        self.launch_button.pack(side=tk.BOTTOM, pady=self.layout_padding)

    def create_status_bar(self):
        self.status_var = tk.StringVar(value="准备就绪")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.RIDGE, anchor=tk.W, foreground="gray")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message):
        self.status_var.set(message)

    def show_about(self, icon=None, item=None):
        pady = self.layout_padding // 2
        self.about_window = tk.Toplevel(self.root)
        self.about_window.title("关于")
        self.about_window.iconbitmap(get_asset("icon.ico"))
        self.about_window.geometry(f"+{self.position_right}+{self.position_top}")
        self.about_window.protocol("WM_DELETE_WINDOW", lambda: self.on_about_window_closing(create_tray=icon is not None))
        self.app_name_label = tk.Label(self.about_window, text=f"{APP_NAME} v{VERSION}")
        self.app_name_label.pack(padx=self.control_padding, pady=pady)
        accent_color = THEME_COLOR[self.theme]["accent"]

        self.author_label = tk.Label(self.about_window, text="作者：Chenglong Ma", fg=accent_color, cursor="hand2")
        self.author_label.pack(padx=self.control_padding, pady=pady)
        self.author_label.bind("<Button-1>", lambda event: open_my_homepage())

        self.homepage_label = tk.Label(self.about_window, text=f"GitHub：{REPO_NAME}", fg=accent_color, cursor="hand2")
        self.homepage_label.pack(padx=self.control_padding, pady=pady)
        self.homepage_label.bind("<Button-1>", lambda event: open_repo_page())

        self.copyright_label = tk.Label(self.about_window, text="Copyright © 2024 Chenglong Ma. All rights reserved.")
        self.copyright_label.pack(padx=self.control_padding, pady=pady)

    def on_about_window_closing(self, create_tray=False):
        self.about_window.destroy()

    def no_new_version_fn(self):
        messagebox.showinfo("检查更新", "当前已是最新版本")
        self.update_status("当前已是最新版本")

    def start_game(self, *settings):
        self.update_status("正在启动游戏...")
        game_clients_in_settings = [os.path.join(setting['product_install_root'], "Riot Client/RiotClientServices.exe") for setting in settings]
        game_clients = filter_existing_files(to_list(self.game_client) + game_clients_in_settings)
        if not game_clients or len(game_clients) == 0:
            self.update_status("未找到 RiotClientServices.exe，请手动启动游戏。")
            return
        if len(game_clients) > 1:
            msg = "请从以下选项中选择一个游戏启动路径"
            title = "找到多个游戏路径，请选择一个"
            choice = easygui.choicebox(msg, title, game_clients)
            if not choice:
                return
            game_clients = [choice]

        self.update_status("英雄联盟，启动！")
        self.game_client = os.path.normpath(game_clients[0])
        subprocess.run(['explorer.exe', self.game_client], check=False)

    def start(self):
        self.update_status("正在更新配置文件...")
        settings = []
        for setting_file in self.setting_files:
            setting = update_settings(setting_file, self.selected_locale, msg_callback_fn=self.update_status)
            if setting:
                settings.append(setting)

        if len(settings) == 0:
            messagebox.showerror("错误", "配置文件更新失败，无法启动游戏。")
            return

        self.start_observers()
        self.start_game(*settings)
        self.on_window_minimizing(True)

    def stop_observers(self):
        print("Stopping observer...")
        for observer in self.observers:
            if observer is not None and observer.is_alive():
                observer.stop()
                observer.join()
                print("Observer stopped")
        self.observers = []

    def start_observers(self):
        event_handler = FileWatcher(*self.setting_files, selected_locale=self.selected_locale)
        unique_dirs = set(os.path.dirname(file) for file in self.setting_files)
        for directory in unique_dirs:
            observer = Observer()
            observer.schedule(event_handler, path=directory, recursive=False)
            observer.start()
            self.observers.append(observer)
        print(f"Start Watching...")

    def detect_metadata_file(self):
        is_yes = tk.messagebox.askyesno("提示", "您确定要重新检测以修改已有配置？")
        if is_yes:
            setting_files = detect_metadata_file()
            if setting_files:
                self.setting_files = setting_files
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
                self.setting_files = [selected_file]
                self.sync_config()
                msg = "游戏配置文件已更新"
            else:
                msg = "未找到有效配置，将继续使用之前的配置"
            self.update_status(msg)
            tk.messagebox.showinfo("提示", msg)

    def on_locale_changed(self, event):
        self.stop_observers()
        current_value = self.locale_var.get()
        self.selected_locale = self.locale_dict[current_value]
        self.update_status(f"语言将被设置为：{current_value}")

    def on_shortcut_changed(self, event):
        current_value = self.shortcut_var.get()
        self.update_status(f"快捷键将被设置为：{current_value}")
        self.quick_chat_dialog.set_hotkey(current_value)

    def on_window_restoring(self, icon: pystray.Icon = None, item=None):
        self.root.after(0, self.root.deiconify)

    def on_window_showing(self, event=None):
        if self.root.winfo_viewable():
            print("Window is already visible")
            return
        print("Window is now visible", event)

    def on_window_minimizing(self, force_minimize=False):
        print("Window is now minimized")
        if force_minimize or self.minimize_on_closing.get():
            self.sync_config()
            self.root.after(0, self.root.withdraw)
        else:
            self.on_window_closing(self.tray_app)

    def run(self):
        self.tray_thread.start()
        self.root.mainloop()
        self.tray_thread.join()

    def sync_config(self):
        default_config = {
            "@注意": r"请使用\或/做为路径分隔符，如 C:\ProgramData 或 C:/ProgramData",
            "@SettingFile": "请在下方填写 league_of_legends.live.product_settings.yaml 文件路径",
            "SettingFile": self.setting_files,
            "@GameClient": "请在下方填写 RiotClientServices.exe 文件路径",
            "GameClient": self.game_client,
            "Locale": self.selected_locale,
            "MinimizeOnClosing": self.minimize_on_closing.get(),
            "Process Name": self.config.get("Process Name", "League of Legends.exe"),
            "QuickChatEnabled": self.quick_chat_enabled.get(),
            "QuickChatShortcut": self.shortcut_var.get(),
            "QuickChatDoc": QUICK_CHAT_DOC,
        }
        self.config.update(default_config)
        self.config.update(self.quick_chat_dialog.user_config)
        write_json(CONFIG_FILENAME, self.config)
        self.ui_config["Theme"] = self.theme
        self.ui_config.update(self.quick_chat_dialog.ui_config)
        write_json(GUI_CONFIG_FILENAME, self.ui_config)
        print("Configuration file updated")

    def on_window_closing(self, icon: pystray.Icon = None, item=None):

        close = messagebox.askyesno("退出", "退出后再启动游戏时文本和语音将恢复为默认设置\n您确定要退出吗？")
        if close:
            self.stop_observers()
            if icon:
                icon.stop()
            self.sync_config()
            self.root.after(0, self.root.destroy)


    def show_window(self):
        print('Showing window')

        if not self.root.winfo_viewable():
            self.root.deiconify()

        self.root.lift()
        self.root.focus_force()

        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
