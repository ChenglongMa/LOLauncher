import os

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QAction, QCloseEvent, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
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
from core.launcher import FileWatcher, start_game
from core.platform import open_homepage, open_repo_page
from core.quick_chat import create_quick_chat_file
from core.updates import check_for_updates
from ui_qt.dialogs import QtDialogService, ensure_qapplication
from ui_qt.fluent import ComboBox, PrimaryPushButton, PushButton, SwitchButton, apply_theme
from ui_qt.quick_chat import QuickChatWindow


class MainWindow(QMainWindow):
    def __init__(self, app: "App"):
        super().__init__()
        self.app = app
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setWindowIcon(app.icon)
        self.setMinimumSize(420, 520)
        self.resize(460, 560)
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("准备就绪")
        self.create_menu_bar()
        self.setCentralWidget(self.create_content())
        self.apply_styles()

    def create_menu_bar(self) -> None:
        setting_menu = self.menuBar().addMenu("设置")

        auto_detect_action = QAction("自动检测游戏配置文件", self)
        auto_detect_action.triggered.connect(self.app.detect_metadata_file)
        setting_menu.addAction(auto_detect_action)

        choose_file_action = QAction("手动选择游戏配置文件", self)
        choose_file_action.triggered.connect(self.app.choose_metadata_file)
        setting_menu.addAction(choose_file_action)

        process_action = QAction("设置进程名称", self)
        process_action.triggered.connect(self.app.set_process_name)
        setting_menu.addAction(process_action)
        setting_menu.addSeparator()

        theme_action = QAction("切换颜色主题", self)
        theme_action.triggered.connect(self.app.toggle_theme)
        setting_menu.addAction(theme_action)

        self.minimize_on_close_action = QAction("关闭时最小化到托盘", self)
        self.minimize_on_close_action.setCheckable(True)
        self.minimize_on_close_action.setChecked(self.app.minimize_on_closing)
        self.minimize_on_close_action.toggled.connect(self.app.set_minimize_on_closing)
        setting_menu.addAction(self.minimize_on_close_action)

        self.start_directly_action = QAction("下次直接启动游戏", self)
        self.start_directly_action.setCheckable(True)
        self.start_directly_action.setChecked(self.app.start_game_directly)
        self.start_directly_action.toggled.connect(self.app.set_start_game_directly)
        setting_menu.addAction(self.start_directly_action)

        help_menu = self.menuBar().addMenu("帮助")
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.app.show_about)
        help_menu.addAction(about_action)

        update_action = QAction("检查更新", self)
        update_action.triggered.connect(lambda: check_for_updates(self.app.dialog, lambda msg: self.app.dialog.info("检查更新", msg)))
        help_menu.addAction(update_action)

    def create_content(self) -> QWidget:
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 20, 22, 16)
        layout.setSpacing(18)

        title = QLabel("LOLauncher", root)
        title.setObjectName("TitleLabel")
        subtitle = QLabel("英雄联盟语言与一键喊话工具", root)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        locale_group = self.create_locale_group(root)
        quick_chat_group = self.create_quick_chat_group(root)
        layout.addWidget(locale_group)
        layout.addWidget(quick_chat_group)
        layout.addStretch(1)

        launch_row = QHBoxLayout()
        launch_row.addStretch(1)
        self.app.launch_button = PrimaryPushButton("英雄联盟，启动！", root)
        self.app.launch_button.setIcon(QIcon(get_asset("button_icon.png")))
        self.app.launch_button.clicked.connect(self.app.start)
        self.app.launch_button.setMinimumHeight(52)
        launch_row.addWidget(self.app.launch_button)
        launch_row.addStretch(1)
        layout.addLayout(launch_row)
        return root

    def create_locale_group(self, parent: QWidget) -> QWidget:
        group = QGroupBox("语言设置", parent)
        layout = QVBoxLayout(group)
        self.app.locale_combo = ComboBox(group)
        self.app.locale_combo.addItems(list(self.app.locale_dict.keys()))
        self.app.locale_combo.setCurrentText(LOCALE_CODES[self.app.selected_locale])
        self.app.locale_combo.currentTextChanged.connect(self.app.on_locale_changed)
        layout.addWidget(self.app.locale_combo)
        return group

    def create_quick_chat_group(self, parent: QWidget) -> QWidget:
        group = QGroupBox("一键喊话设置", parent)
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        warning = QLabel('<a href="{0}">⚡ 使用前请仔细阅读 注意事项</a>'.format(self.app.quick_chat_doc), group)
        warning.setOpenExternalLinks(True)
        warning.setAlignment(Qt.AlignCenter)
        warning.setObjectName("WarningLabel")
        layout.addWidget(warning)

        if SwitchButton is not None:
            self.app.quick_chat_switch = SwitchButton("一键喊话", group)
            self.app.quick_chat_switch.setChecked(self.app.quick_chat_enabled)
            self.app.quick_chat_switch.checkedChanged.connect(self.app.on_quick_chat_enabled_changed)
            layout.addWidget(self.app.quick_chat_switch, alignment=Qt.AlignCenter)
        else:
            self.app.quick_chat_switch = QCheckBox("一键喊话", group)
            self.app.quick_chat_switch.setChecked(self.app.quick_chat_enabled)
            self.app.quick_chat_switch.toggled.connect(self.app.on_quick_chat_enabled_changed)
            layout.addWidget(self.app.quick_chat_switch, alignment=Qt.AlignCenter)

        shortcut_row = QHBoxLayout()
        shortcut_row.addWidget(QLabel("快捷键", group))
        self.app.shortcut_combo = ComboBox(group)
        available_shortcuts = ["`", "Alt", "Ctrl", "Shift", "Tab"]
        if self.app.quick_chat_shortcut not in available_shortcuts:
            available_shortcuts.append(self.app.quick_chat_shortcut)
        self.app.shortcut_combo.addItems(available_shortcuts)
        self.app.shortcut_combo.setCurrentText(self.app.quick_chat_shortcut)
        self.app.shortcut_combo.setEnabled(self.app.quick_chat_enabled)
        self.app.shortcut_combo.currentTextChanged.connect(self.app.on_shortcut_changed)
        shortcut_row.addWidget(self.app.shortcut_combo, stretch=1)
        layout.addLayout(shortcut_row)

        self.app.set_chat_button = PushButton("设置喊话内容", group)
        self.app.set_chat_button.setEnabled(self.app.quick_chat_enabled)
        self.app.set_chat_button.clicked.connect(self.app.quick_chat_window.open_quick_chat_file)
        layout.addWidget(self.app.set_chat_button)
        return group

    def apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                font-family: "Microsoft YaHei UI";
                font-size: 14px;
            }
            QLabel#TitleLabel {
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#SubtitleLabel {
                color: #666666;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid rgba(128, 128, 128, 0.35);
                border-radius: 8px;
                margin-top: 12px;
                padding: 18px 14px 14px 14px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                font-weight: 600;
            }
            QLabel#WarningLabel {
                background: rgba(200, 155, 60, 0.18);
                border: 1px solid rgba(200, 155, 60, 0.55);
                border-radius: 6px;
                padding: 8px;
            }
            """
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.app.handle_close_event(event)


class App(QObject):
    show_requested = Signal()

    def __init__(
        self,
        setting_files: list[str],
        config: dict,
        gui_config: dict,
        dialog: QtDialogService | None = None,
        config_filename: str = CONFIG_FILENAME,
        gui_config_filename: str = GUI_CONFIG_FILENAME,
        quick_chat_filename: str = QUICK_CHAT_FILENAME,
    ):
        super().__init__()
        self.qt_app = ensure_qapplication()
        self.qt_app.setFont(QFont("Microsoft YaHei UI", 10))
        self.setting_files = setting_files
        self.config = config
        self.ui_config = gui_config
        self.config_filename = config_filename
        self.gui_config_filename = gui_config_filename
        self.quick_chat_filename = quick_chat_filename
        self.locale_dict = {value: key for key, value in LOCALE_CODES.items()}
        self.selected_locale = config.get("Locale", "zh_CN")
        if self.selected_locale not in LOCALE_CODES:
            self.selected_locale = "zh_CN"
        self.game_client = config.get("GameClient", "")
        self.theme = gui_config.get("Theme", "light")
        self.minimize_on_closing = bool(config.get("MinimizeOnClosing", True))
        self.start_game_directly = bool(config.get("StartGameDirectly", False))
        self.quick_chat_doc = config.get("QuickChatDoc", QUICK_CHAT_DOC)
        self.quick_chat_enabled = bool(config.get("QuickChatEnabled", False))
        self.quick_chat_shortcut = config.get("QuickChatShortcut", "`")
        self._syncing_quick_chat_controls = False
        self.observers: list[Observer] = []

        apply_theme(self.theme)
        self.icon = QIcon(get_asset("icon.ico"))
        self.qt_app.setWindowIcon(self.icon)
        self.dialog = dialog or QtDialogService()

        self.window: MainWindow | None = None
        self.quick_chat_window: QuickChatWindow | None = None
        self.tray_icon: QSystemTrayIcon | None = None
        self.quick_chat_tray_action: QAction | None = None

        self.quick_chat_window = QuickChatWindow(self, self.config, self.ui_config, self.quick_chat_filename)
        self.window = MainWindow(self)
        if hasattr(self.dialog, "set_parent"):
            self.dialog.set_parent(self.window)
        self.tray_icon = self.create_tray_icon()
        self.show_requested.connect(self.show_window)

        if self.quick_chat_enabled:
            self.quick_chat_window.set_hotkey(self.quick_chat_shortcut)

    def create_tray_icon(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(QIcon(get_asset("tray_icon.png")), self.window)
        tray.setToolTip(f"{APP_NAME} v{VERSION}")
        menu = QMenu(self.window)

        show_action = QAction("显示主窗口", menu)
        show_action.triggered.connect(self.show_window)
        menu.addAction(show_action)

        self.quick_chat_tray_action = QAction("一键喊话", menu)
        self.quick_chat_tray_action.setCheckable(True)
        self.quick_chat_tray_action.setChecked(self.quick_chat_enabled)
        self.quick_chat_tray_action.toggled.connect(self.set_quick_chat_enabled)
        menu.addAction(self.quick_chat_tray_action)

        about_action = QAction("帮助", menu)
        about_action.triggered.connect(self.show_about)
        menu.addAction(about_action)

        exit_action = QAction("退出", menu)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)

        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: self.show_window() if reason == QSystemTrayIcon.DoubleClick else None)
        tray.show()
        return tray

    def request_show(self) -> None:
        self.show_requested.emit()

    def run(self) -> int:
        assert self.window is not None
        self.window.show()
        result = self.qt_app.exec()
        if self.start_game_directly:
            self.start()
        return result

    def update_status(self, message: str) -> None:
        if self.window is not None:
            self.window.statusBar().showMessage(message)

    def set_minimize_on_closing(self, checked: bool) -> None:
        self.minimize_on_closing = checked

    def set_start_game_directly(self, checked: bool) -> None:
        self.start_game_directly = checked

    def set_quick_chat_enabled(self, checked: bool) -> None:
        if self._syncing_quick_chat_controls:
            return
        self._syncing_quick_chat_controls = True
        try:
            if self.quick_chat_switch is not None and self.quick_chat_switch.isChecked() != checked:
                self.quick_chat_switch.blockSignals(True)
                self.quick_chat_switch.setChecked(checked)
                self.quick_chat_switch.blockSignals(False)
            self.on_quick_chat_enabled_changed(checked)
        finally:
            self._syncing_quick_chat_controls = False

    def on_quick_chat_enabled_changed(self, checked: bool) -> None:
        if checked and not self.config.get("QuickChatNoteNotAsk", False):
            decision = self.dialog.choose(
                "启用前的准备",
                '您是否已根据《注意事项》设置好"无边框"模式？',
                ["已设置好", "还没有", "已设置好，不要再提醒"],
            )
            if decision in (None, "还没有"):
                self.quick_chat_enabled = False
                if self.quick_chat_switch is not None and self.quick_chat_switch.isChecked():
                    self.quick_chat_switch.blockSignals(True)
                    self.quick_chat_switch.setChecked(False)
                    self.quick_chat_switch.blockSignals(False)
                self.apply_quick_chat_state(False)
                return
            if decision == "已设置好，不要再提醒":
                self.config["QuickChatNoteNotAsk"] = True

        self.quick_chat_enabled = bool(checked)
        self.apply_quick_chat_state(self.quick_chat_enabled)

    def apply_quick_chat_state(self, enabled: bool) -> None:
        if self.shortcut_combo is not None:
            self.shortcut_combo.setEnabled(enabled)
        if self.set_chat_button is not None:
            self.set_chat_button.setEnabled(enabled)
        if self.quick_chat_tray_action is not None:
            self.quick_chat_tray_action.blockSignals(True)
            self.quick_chat_tray_action.setChecked(enabled)
            self.quick_chat_tray_action.blockSignals(False)

        if enabled:
            self.update_status("一键喊话已启用")
            create_quick_chat_file(self.config_filename)
            self.quick_chat_window.set_hotkey(self.quick_chat_shortcut)
        else:
            self.update_status("一键喊话已禁用")
            self.quick_chat_window.disable_hotkey()

    def on_locale_changed(self, text: str) -> None:
        self.stop_observers()
        self.selected_locale = self.locale_dict[text]
        self.update_status(f"语言将被设置为：{text}")

    def on_shortcut_changed(self, text: str) -> None:
        self.quick_chat_shortcut = text
        self.update_status(f"快捷键将被设置为：{text}")
        if self.quick_chat_enabled:
            self.quick_chat_window.set_hotkey(text)

    def toggle_theme(self) -> None:
        self.theme = "light" if "dark" in self.theme.lower() else "dark"
        apply_theme(self.theme)
        self.update_status(f"已切换到 {self.theme} 主题")

    def set_process_name(self) -> None:
        process_name = self.dialog.input_text(
            "设置进程名称",
            "请输入进程名称",
            self.config.get("Process Name", "League of Legends.exe"),
        )
        if process_name:
            self.config["Process Name"] = process_name
            self.sync_config()
            self.update_status(f"进程名称已设置为：{process_name}")

    def detect_metadata_file(self) -> None:
        if not self.dialog.confirm("提示", "您确定要重新检测以修改已有配置？"):
            return
        setting_files = detect_metadata_file()
        if setting_files:
            self.setting_files = setting_files
            self.sync_config()
            msg = "游戏配置文件已更新"
        else:
            msg = "未找到有效配置，将继续使用之前的配置"
        self.update_status(msg)
        self.dialog.info("提示", msg)

    def choose_metadata_file(self) -> None:
        if not self.dialog.confirm("提示", "已自动检测到游戏配置文件，您确定要手动选择吗？"):
            return
        selected_file = open_metadata_file_dialog(self.dialog, "请选择 league_of_legends.live.product_settings.yaml 文件")
        if selected_file:
            self.setting_files = [selected_file]
            self.sync_config()
            msg = "游戏配置文件已更新"
        else:
            msg = "未找到有效配置，将继续使用之前的配置"
        self.update_status(msg)
        self.dialog.info("提示", msg)

    def show_about(self) -> None:
        message = (
            f"{APP_NAME} v{VERSION}\n\n"
            "作者：Chenglong Ma\n"
            f"GitHub：{REPO_NAME}\n\n"
            "Copyright © 2024 Chenglong Ma. All rights reserved."
        )
        self.dialog.info("关于", message)

    def open_homepage(self) -> None:
        open_homepage()

    def open_repo_page(self) -> None:
        open_repo_page(REPO_NAME)

    def start(self) -> None:
        self.update_status("正在更新配置文件...")
        settings = []
        for setting_file in self.setting_files:
            setting = update_settings(setting_file, self.selected_locale, msg_callback_fn=self.update_status)
            if setting:
                settings.append(setting)

        if not settings:
            self.dialog.error("错误", "配置文件更新失败，无法启动游戏。")
            return

        self.start_observers()
        self.update_status("正在启动游戏...")
        selected_client = start_game(self.game_client, tuple(settings), self.dialog)
        if not selected_client:
            self.update_status("未找到 RiotClientServices.exe，请手动启动游戏。")
            return
        self.game_client = os.path.normpath(selected_client)
        self.update_status("英雄联盟，启动！")
        self.minimize_window(force=True)

    def start_observers(self) -> None:
        event_handler = FileWatcher(*self.setting_files, selected_locale=self.selected_locale)
        unique_dirs = set(os.path.dirname(file) for file in self.setting_files)
        for directory in unique_dirs:
            observer = Observer()
            observer.schedule(event_handler, path=directory, recursive=False)
            observer.start()
            self.observers.append(observer)
        print("Start Watching...")

    def stop_observers(self) -> None:
        print("Stopping observer...")
        for observer in self.observers:
            if observer is not None and observer.is_alive():
                observer.stop()
                observer.join()
                print("Observer stopped")
        self.observers = []

    def sync_config(self) -> None:
        config = build_app_config(
            existing_config=self.config,
            setting_files=self.setting_files,
            game_client=self.game_client,
            selected_locale=self.selected_locale,
            minimize_on_closing=self.minimize_on_closing,
            start_game_directly=self.start_game_directly,
            quick_chat_enabled=self.quick_chat_enabled,
            quick_chat_shortcut=self.quick_chat_shortcut,
        )
        self.config = config
        self.quick_chat_window.user_config = self.config
        write_json(self.config_filename, config)

        gui_config = build_gui_config(
            existing_config=self.ui_config,
            theme=self.theme,
            quick_chat_ui_config=self.quick_chat_window.export_ui_config(),
        )
        self.ui_config = gui_config
        write_json(self.gui_config_filename, gui_config)
        print("Configuration file updated")

    def minimize_window(self, force: bool = False) -> None:
        if force or self.minimize_on_closing:
            self.sync_config()
            self.window.hide()
        else:
            self.exit_app()

    def handle_close_event(self, event: QCloseEvent) -> None:
        if self.minimize_on_closing:
            self.minimize_window(force=True)
            event.ignore()
        elif self.confirm_exit():
            event.accept()
            self.shutdown()
            self.qt_app.quit()
        else:
            event.ignore()

    def confirm_exit(self) -> bool:
        return self.dialog.confirm("退出", "退出后再启动游戏时文本和语音将恢复为默认设置\n您确定要退出吗？")

    def exit_app(self) -> None:
        if not self.confirm_exit():
            return
        self.shutdown()
        self.qt_app.quit()

    def shutdown(self) -> None:
        self.stop_observers()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        if self.quick_chat_window is not None:
            self.quick_chat_window.disable_hotkey()
        self.sync_config()

    def show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
