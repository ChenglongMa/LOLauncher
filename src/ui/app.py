import os
import subprocess
import threading
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import font, ttk

import pystray
import sv_ttk
from PIL import Image, ImageTk
from watchdog.observers import Observer

from assets import get_asset
from core.config import (
    build_app_config,
    build_gui_config,
    detect_metadata_file,
    open_metadata_file_dialog,
    update_settings,
    write_json,
)
from core.constants import (
    APP_NAME,
    CONFIG_FILENAME,
    GUI_CONFIG_FILENAME,
    LOCALE_CODES,
    QUICK_CHAT_DOC,
    QUICK_CHAT_FILENAME,
    REPO_NAME,
    VERSION,
)
from core.dialogs import DialogService
from core.launcher import FileWatcher, start_game
from core.platform import get_primary_work_area, get_window_size, open_homepage, open_repo_page
from core.quick_chat import create_quick_chat_file
from core.updates import check_for_updates
from ui.dialogs import TkDialogService
from ui.quick_chat import QuickChatDialog
from ui.utils import THEME_COLOR, create_warning_label


class App:
    def __init__(
        self,
        setting_files: list[str],
        config: dict,
        gui_config: dict,
        *,
        root: tk.Tk | None = None,
        dialog: DialogService | None = None,
        config_filename: str = CONFIG_FILENAME,
        gui_config_filename: str = GUI_CONFIG_FILENAME,
        quick_chat_filename: str = QUICK_CHAT_FILENAME,
    ):
        self.root = root if root is not None else tk.Tk()
        self.root.withdraw()
        self.dialog = dialog or TkDialogService(self.root)
        self.setting_files = setting_files
        self.config = config
        self.ui_config = gui_config
        self.config_filename = config_filename
        self.gui_config_filename = gui_config_filename
        self.quick_chat_filename = quick_chat_filename
        self.game_client = config.get("GameClient", "")
        locale = config.get("Locale", "zh_CN")
        self.selected_locale = locale if isinstance(locale, str) and locale in LOCALE_CODES else "zh_CN"
        self.locale_by_label = {label: code for code, label in LOCALE_CODES.items()}
        self.quick_chat_enabled = bool(config.get("QuickChatEnabled", False))
        self.theme = "dark" if "dark" in str(gui_config.get("Theme", "light")).lower() else "light"
        self.observers: list[Observer] = []
        self.ui_events = SimpleQueue()
        self.ui_timer = None
        self.closed = False
        self.scale = round(self.root.winfo_fpixels("1i")) / 96
        self.control_padding = round(10 * self.scale)
        self.layout_padding = round(15 * self.scale)

        self.apply_theme()
        for font_name in font.names(root=self.root):
            font.nametofont(font_name, root=self.root).config(family="Microsoft YaHei UI")
        # Sun Valley declares these fonts in pixels, so Tk's point scaling does not affect them.
        for name, size in (("SunValleyCaptionFont", 12), ("SunValleyBodyFont", 14)):
            font.nametofont(name, root=self.root).configure(size=-round(size * self.scale))
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.iconbitmap(get_asset("icon.ico"))
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_closing)
        self.create_menu_bar()
        self.create_launch_controls()
        self.create_locale_groupbox()
        self.create_quick_chat_groupbox()
        self.position_main_window()

        self.quick_chat_dialog = QuickChatDialog(self)
        self.tray_app = self.create_tray_app()
        self.update_quick_chat_controls()
        if self.quick_chat_enabled:
            self.quick_chat_dialog.set_hotkey(self.shortcut_var.get())

    def position_main_window(self) -> None:
        self.root.update_idletasks()
        width = max(round(350 * self.scale), self.root.winfo_reqwidth())
        height = max(round(420 * self.scale), self.root.winfo_reqheight())
        self.root.minsize(width, height)
        self.root.maxsize(max(width, round(400 * self.scale)), max(height, round(470 * self.scale)))
        self.root.geometry(f"{width}x{height}")
        self.root.update_idletasks()

        outer_width, outer_height = get_window_size(int(self.root.wm_frame(), 0)) or (width, height)
        left, top, right, bottom = get_primary_work_area() or (
            0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight(),
        )
        x = left + max(0, (right - left - outer_width) // 2)
        y = top + max(0, (bottom - top - outer_height) // 2)
        self.root.geometry(f"+{x}+{y}")

    def create_menu_bar(self) -> None:
        menu_bar = tk.Menu(self.root)
        settings = tk.Menu(menu_bar, tearoff=False)
        settings.add_command(label="自动检测游戏配置文件", command=self.detect_metadata_file)
        settings.add_command(label="手动选择游戏配置文件", command=self.choose_metadata_file)
        settings.add_command(label="设置进程名称", command=self.set_process_name)
        settings.add_separator()
        settings.add_command(label="切换颜色主题", command=self.toggle_theme)
        self.minimize_on_closing = tk.BooleanVar(self.root, value=bool(self.config.get("MinimizeOnClosing", True)))
        settings.add_checkbutton(label="关闭时最小化到托盘", variable=self.minimize_on_closing)
        self.start_game_directly = tk.BooleanVar(self.root, value=bool(self.config.get("StartGameDirectly", False)))
        settings.add_checkbutton(label="下次直接启动游戏", variable=self.start_game_directly)
        menu_bar.add_cascade(label="设置", menu=settings)
        help_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu.add_command(label="关于", command=self.show_about)
        help_menu.add_command(label="检查更新", command=lambda: check_for_updates(
            self.dialog, lambda message: self.dialog.info("检查更新", message),
        ))
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menu_bar)

    def create_locale_groupbox(self) -> None:
        group = ttk.LabelFrame(self.root, text="语言设置")
        self.locale_dropdown = ttk.Combobox(group, values=list(self.locale_by_label), state="readonly")
        self.locale_dropdown.set(LOCALE_CODES[self.selected_locale])
        self.locale_dropdown.pack(fill=tk.X, padx=self.control_padding, pady=self.control_padding)
        self.locale_dropdown.bind("<<ComboboxSelected>>", self.on_locale_changed)
        group.pack(fill=tk.X, padx=self.layout_padding, pady=self.layout_padding)

    def create_quick_chat_groupbox(self) -> None:
        group = ttk.LabelFrame(self.root, text="一键喊话设置")
        self.warning_label = create_warning_label(
            group, "⚡ 使用前请仔细阅读", "注意事项", self.config.get("QuickChatDoc", QUICK_CHAT_DOC), theme=self.theme,
        )
        self.warning_label.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.X)
        self.quick_chat_var = tk.BooleanVar(self.root, value=self.quick_chat_enabled)
        ttk.Checkbutton(group, text="一键喊话", variable=self.quick_chat_var, style="Switch.TCheckbutton",
                        command=lambda: self.set_quick_chat_enabled(self.quick_chat_var.get())).pack()

        shortcut_frame = ttk.Frame(group)
        ttk.Label(shortcut_frame, text="快捷键").pack(side=tk.LEFT, padx=self.control_padding)
        shortcuts = ["`", "Alt", "Ctrl", "Shift", "Tab"]
        shortcut = self.config.get("QuickChatShortcut", "`")
        if shortcut not in shortcuts:
            shortcuts.append(shortcut)
        self.shortcut_var = tk.StringVar(self.root, value=shortcut)
        self.shortcut_dropdown = ttk.Combobox(shortcut_frame, textvariable=self.shortcut_var, values=shortcuts)
        self.shortcut_dropdown.bind("<<ComboboxSelected>>", self.on_shortcut_changed)
        self.shortcut_dropdown.pack(side=tk.RIGHT)
        shortcut_frame.pack(padx=self.layout_padding)
        self.set_chat_button = ttk.Button(group, text="设置喊话内容", command=self.open_quick_chat_file)
        self.set_chat_button.pack(padx=self.control_padding, pady=self.control_padding, fill=tk.X)
        group.pack(fill=tk.X, padx=self.layout_padding, pady=self.layout_padding)

    def create_launch_controls(self) -> None:
        self.status_var = tk.StringVar(self.root, value="准备就绪")
        status = ttk.Label(self.root, textvariable=self.status_var, relief=tk.RIDGE, anchor=tk.W, width=1)
        status.pack(side=tk.BOTTOM, fill=tk.X)

        with Image.open(get_asset("button_icon.png")) as icon:
            size = (round(icon.width * self.scale), round(icon.height * self.scale))
            self.launch_image = ImageTk.PhotoImage(icon.resize(size, Image.Resampling.LANCZOS), master=self.root)
        self.launch_button = ttk.Button(self.root, text="英雄联盟，启动！", image=self.launch_image, compound=tk.LEFT,
                                        command=self.start, style="CustomAccent.TButton")
        self.launch_button.pack(side=tk.BOTTOM, pady=self.layout_padding)

    def create_tray_app(self) -> pystray.Icon:
        menu = pystray.Menu(
            pystray.MenuItem("显示主窗口", lambda *_: self.post_to_ui(self.show_window), default=True),
            pystray.MenuItem("一键喊话", lambda *_: self.post_to_ui(self.toggle_quick_chat),
                             checked=lambda _: self.quick_chat_enabled),
            pystray.MenuItem("帮助", lambda *_: self.post_to_ui(self.show_about)),
            pystray.MenuItem("退出", lambda *_: self.post_to_ui(self.exit_app)),
        )
        with Image.open(get_asset("tray_icon.png")) as image:
            return pystray.Icon(APP_NAME, image.copy(), f"{APP_NAME} v{VERSION}", menu)

    def post_to_ui(self, callback) -> None:
        self.ui_events.put(callback)

    def process_ui_events(self) -> None:
        self.ui_timer = self.root.after(75, self.process_ui_events)
        while True:
            try:
                callback = self.ui_events.get_nowait()
            except Empty:
                return
            callback()

    def request_show(self) -> None:
        self.post_to_ui(self.show_window)

    def run(self) -> int:
        self.root.deiconify()
        self.ui_timer = self.root.after(0, self.process_ui_events)
        threading.Thread(target=self.tray_app.run, daemon=True).start()
        if self.start_game_directly.get():
            self.root.after_idle(self.start)
        try:
            self.root.mainloop()
        finally:
            self.shutdown()
        return 0

    def apply_theme(self) -> None:
        sv_ttk.set_theme(self.theme, self.root)
        style = ttk.Style(self.root)
        for name, padding in (("TButton", (8, 2, 8, 3)), ("TCombobox", (6, 1, 0, 2))):
            style.configure(name, padding=tuple(round(size * self.scale) for size in padding))
        style.configure("CustomAccent.TButton", font=("Microsoft YaHei UI", 16, "bold"))

    def toggle_theme(self) -> None:
        self.theme = "light" if self.theme == "dark" else "dark"
        self.apply_theme()
        colors = THEME_COLOR[self.theme]
        self.warning_label.config(background=colors["warning_bg"], foreground=colors["warning_fg"])
        self.warning_label.tag_config("link", foreground=colors["accent"])
        self.update_status(f"已切换到 {self.theme} 主题")

    def toggle_quick_chat(self) -> None:
        self.set_quick_chat_enabled(not self.quick_chat_enabled)

    def set_quick_chat_enabled(self, checked: bool) -> None:
        if checked and not self.config.get("QuickChatNoteNotAsk", False):
            decision = self.dialog.choose(
                "启用前的准备", '您是否已根据《注意事项》设置好"无边框"模式？',
                ["已设置好", "还没有", "已设置好，不要再提醒"],
            )
            if decision in (None, "还没有"):
                checked = False
            elif decision == "已设置好，不要再提醒":
                self.config["QuickChatNoteNotAsk"] = True
        self.quick_chat_enabled = checked
        self.update_quick_chat_controls()
        self.tray_app.update_menu()
        if checked:
            self.update_status("一键喊话已启用")
            create_quick_chat_file(self.config_filename)
            self.quick_chat_dialog.set_hotkey(self.shortcut_var.get())
        else:
            self.update_status("一键喊话已禁用")
            self.quick_chat_dialog.disable_hotkey()

    def update_quick_chat_controls(self) -> None:
        self.quick_chat_var.set(self.quick_chat_enabled)
        self.shortcut_dropdown.configure(state="readonly" if self.quick_chat_enabled else tk.DISABLED)
        self.set_chat_button.configure(state=tk.NORMAL if self.quick_chat_enabled else tk.DISABLED)

    def open_quick_chat_file(self) -> None:
        create_quick_chat_file(self.config_filename)
        subprocess.Popen(["notepad.exe", self.quick_chat_filename])

    def on_shortcut_changed(self, _event=None) -> None:
        shortcut = self.shortcut_var.get()
        self.update_status(f"快捷键将被设置为：{shortcut}")
        if self.quick_chat_enabled:
            self.quick_chat_dialog.set_hotkey(shortcut)

    def on_locale_changed(self, _event=None) -> None:
        self.stop_observers()
        label = self.locale_dropdown.get()
        self.selected_locale = self.locale_by_label[label]
        self.update_status(f"语言将被设置为：{label}")

    def set_process_name(self) -> None:
        name = self.dialog.input_text(
            "设置进程名称", "请输入进程名称", self.config.get("Process Name", "League of Legends.exe"),
        )
        if name:
            self.config["Process Name"] = name
            self.sync_config()
            self.update_status(f"进程名称已设置为：{name}")

    def detect_metadata_file(self) -> None:
        self.setting_files = detect_metadata_file(self.config.get("SettingFile"))
        if self.setting_files:
            message = f"找到 {len(self.setting_files)} 个有效的游戏配置文件"
        else:
            message = "未找到游戏配置文件，请检查安装或手动选择配置文件"
        self.update_status(message if self.setting_files else "未找到游戏配置文件")
        self.dialog.info("提示", message)

    def choose_metadata_file(self) -> None:
        selected_file = open_metadata_file_dialog(self.dialog)
        if selected_file:
            self.config["SettingFile"] = [selected_file]
            self.sync_config()
            message = "已保存手动选择的配置文件"
        else:
            message = "未选择有效的游戏配置文件"
        self.update_status(message)
        self.dialog.info("提示", message)

    def show_about(self) -> None:
        about = tk.Toplevel(self.root)
        about.title("关于")
        about.iconbitmap(get_asset("icon.ico"))
        about.resizable(False, False)
        ttk.Label(about, text=f"{APP_NAME} v{VERSION}").pack(padx=16, pady=(12, 6))
        ttk.Button(about, text="作者：Chenglong Ma", command=open_homepage).pack(padx=16, fill=tk.X)
        ttk.Button(about, text=f"GitHub：{REPO_NAME}", command=lambda: open_repo_page(REPO_NAME)).pack(padx=16, fill=tk.X)
        ttk.Label(about, text="Copyright © 2024 Chenglong Ma. All rights reserved.").pack(padx=16, pady=12)

    def update_status(self, message: str) -> None:
        self.status_var.set(message)

    def start(self) -> None:
        self.update_status("正在更新配置文件...")
        self.setting_files = detect_metadata_file(self.config.get("SettingFile"))
        if not self.setting_files:
            self.update_status("未找到游戏配置文件")
            self.dialog.error("错误", "未找到游戏配置文件，请检查安装或手动选择配置文件。")
            return

        self.stop_observers()
        settings = []
        applied_files = []
        for setting_file in self.setting_files:
            setting = update_settings(setting_file, self.selected_locale)
            if setting is not None:
                settings.append(setting)
                applied_files.append(setting_file)

        failed_count = len(self.setting_files) - len(applied_files)
        summary = f"成功 {len(applied_files)}，失败 {failed_count}"
        if not settings:
            self.update_status(summary)
            self.dialog.error("错误", "配置文件更新失败，请检查文件是否为只读或正在被占用。")
            return

        watch_failures = self.start_observers(applied_files)
        try:
            selected_client = start_game(self.game_client, tuple(settings), self.dialog)
        except OSError as error:
            print(f"无法打开 Riot Client: {error}")
            selected_client = None

        if watch_failures:
            summary += f"，监听失败 {watch_failures}"
        if selected_client:
            self.game_client = selected_client
        else:
            summary += " · 请手动打开 Riot Client"
        self.update_status(summary)
        if selected_client and not (failed_count or watch_failures):
            self.minimize_window()

    def start_observers(self, setting_files: list[str]) -> int:
        watcher = FileWatcher(*setting_files, selected_locale=self.selected_locale)
        failures = 0
        for directory in dict.fromkeys(os.path.dirname(path) for path in setting_files):
            observer = Observer()
            try:
                observer.schedule(watcher, path=directory, recursive=False)
                observer.start()
            except OSError as error:
                print(f"无法监听配置目录 {directory}: {error}")
                failures += 1
            else:
                self.observers.append(observer)
        return failures

    def stop_observers(self) -> None:
        for observer in self.observers:
            if observer.is_alive():
                observer.stop()
                observer.join()
        self.observers.clear()

    def sync_config(self) -> None:
        self.config = build_app_config(
            existing_config=self.config,
            setting_files=self.config.get("SettingFile", []),
            game_client=self.game_client,
            selected_locale=self.selected_locale,
            minimize_on_closing=self.minimize_on_closing.get(),
            start_game_directly=self.start_game_directly.get(),
            quick_chat_enabled=self.quick_chat_enabled,
            quick_chat_shortcut=self.shortcut_var.get(),
        )
        write_json(self.config_filename, self.config)
        self.ui_config = build_gui_config(existing_config=self.ui_config, theme=self.theme)
        write_json(self.gui_config_filename, self.ui_config)

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def minimize_window(self) -> None:
        self.sync_config()
        self.root.withdraw()

    def on_window_closing(self) -> None:
        if self.minimize_on_closing.get():
            self.minimize_window()
        else:
            self.exit_app()

    def exit_app(self) -> None:
        if self.dialog.confirm("退出", "退出后再启动游戏时文本和语音将恢复为默认设置\n您确定要退出吗？"):
            self.root.quit()

    def shutdown(self) -> None:
        if self.closed:
            return
        self.closed = True
        if self.ui_timer is not None:
            self.root.after_cancel(self.ui_timer)
        self.stop_observers()
        self.quick_chat_dialog.disable_hotkey()
        self.tray_app.stop()
        self.sync_config()
