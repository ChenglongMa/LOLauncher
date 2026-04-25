import os
import subprocess
import threading

import keyboard
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QListWidget, QVBoxLayout, QWidget

from assets import get_asset
from core.constants import QUICK_CHAT_FILENAME
from core.platform import is_running
from core.quick_chat import create_quick_chat_file, read_quick_chat_file, send_text_to_lol_chat


class QuickChatWindow(QWidget):
    toggle_requested = Signal()

    def __init__(self, app, config: dict, gui_config: dict, quick_chat_filename: str = QUICK_CHAT_FILENAME):
        super().__init__(app.window)
        self.app = app
        self.user_config = config
        self.ui_config = gui_config
        self.quick_chat_filename = quick_chat_filename
        self.shortcut: str | None = None
        self.lol_pid: int | None = None
        self.lock = threading.Lock()
        self.drag_origin: QPoint | None = None

        self.setWindowTitle("一键喊话")
        self.setWindowIcon(app.icon)
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowOpacity(0.95)

        self.chat_list = QListWidget(self)
        self.chat_list.itemClicked.connect(self.on_chat_selected)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.chat_list)
        self.setStyleSheet(
            """
            QWidget {
                background: #264C47;
                border: 2px solid #927934;
            }
            QListWidget {
                background: #264C47;
                color: #8F7A48;
                border: none;
                font-size: 16px;
            }
            QListWidget::item {
                padding: 8px 10px;
            }
            QListWidget::item:hover,
            QListWidget::item:selected {
                background: #C89B3C;
                color: #010A13;
            }
            """
        )
        self.toggle_requested.connect(self.toggle_window)
        self.restore_geometry()
        self.hide()

    def restore_geometry(self) -> None:
        width = max(int(self.ui_config.get("QuickChatWidth", 300)), 300)
        height = max(int(self.ui_config.get("QuickChatHeight", 220)), 120)
        x = max(int(self.ui_config.get("QuickChatX", 100)), 0)
        y = max(int(self.ui_config.get("QuickChatY", 300)), 0)
        self.setGeometry(x, y, width, height)
        self.setMinimumSize(300, 120)

    def export_ui_config(self) -> dict:
        geo = self.geometry()
        return {
            "QuickChatWidth": geo.width(),
            "QuickChatHeight": geo.height(),
            "QuickChatX": geo.x(),
            "QuickChatY": geo.y(),
        }

    def refresh_chat_list(self) -> None:
        if not os.path.exists(self.quick_chat_filename):
            create_quick_chat_file(self.app.config_filename)
        self.chat_list.clear()
        for text in read_quick_chat_file(self.quick_chat_filename):
            self.chat_list.addItem(text)

    def disable_hotkey(self) -> None:
        if self.shortcut:
            keyboard.remove_hotkey(self.shortcut)
            self.shortcut = None

    def set_hotkey(self, shortcut: str) -> None:
        if not shortcut or shortcut == self.shortcut:
            return
        self.disable_hotkey()
        self.shortcut = shortcut
        keyboard.add_hotkey(self.shortcut, self.toggle_requested.emit)

    def toggle_window(self) -> None:
        if self.isVisible():
            self.hide()
            return

        self.lol_pid = is_running(self.user_config.get("Process Name", "League of Legends.exe"))
        if not self.lol_pid:
            decision = self.app.dialog.choose(
                "提示",
                "游戏对局未开始，是否显示一键喊话对话框？",
                ["是", "取消", "关闭一键喊话"],
            )
            if decision in (None, "取消"):
                return
            if decision == "关闭一键喊话":
                self.app.set_quick_chat_enabled(False)
                self.disable_hotkey()
                return

        self.refresh_chat_list()
        self.show()
        self.raise_()
        self.activateWindow()

    def on_chat_selected(self, item) -> None:
        self.hide()
        if not self.lol_pid:
            print("League of Legends is not running.")
            return
        thread = threading.Thread(target=send_text_to_lol_chat, args=(item.text(), self.lock, self.lol_pid), daemon=True)
        thread.start()

    def open_quick_chat_file(self) -> None:
        if not os.path.exists(self.quick_chat_filename):
            create_quick_chat_file(self.app.config_filename)
        subprocess.run(["notepad.exe", self.quick_chat_filename], check=False)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_origin is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_origin)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_origin = None
        event.accept()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()

