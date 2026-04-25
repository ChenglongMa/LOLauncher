from PySide6.QtCore import Qt

from core.constants import LOCALE_CODES
from ui_qt.app import App
from conftest import FakeDialog


def make_app(tmp_path, config=None, gui_config=None, dialog=None):
    return App(
        ["C:/missing/settings.yaml"],
        config or {},
        gui_config or {},
        dialog=dialog or FakeDialog(),
        config_filename=str(tmp_path / "config.json"),
        gui_config_filename=str(tmp_path / "gui_config.json"),
        quick_chat_filename=str(tmp_path / "quick_chat.txt"),
    )


def test_qt_app_initializes_main_controls(qtbot, tmp_path):
    app = make_app(tmp_path, config={"Locale": "en_US", "QuickChatEnabled": False})
    qtbot.addWidget(app.window)

    assert app.window.windowTitle().startswith("LOLauncher")
    assert app.locale_combo.currentText() == LOCALE_CODES["en_US"]
    assert not app.quick_chat_switch.isChecked()
    assert not app.shortcut_combo.isEnabled()
    assert not app.set_chat_button.isEnabled()

    app.shutdown()


def test_quick_chat_enable_updates_controls_and_tray(qtbot, tmp_path, mocker):
    dialog = FakeDialog(choices=["已设置好，不要再提醒"])
    app = make_app(tmp_path, config={"QuickChatEnabled": False}, dialog=dialog)
    qtbot.addWidget(app.window)
    mocker.patch.object(app.quick_chat_window, "set_hotkey")

    app.set_quick_chat_enabled(True)

    assert app.quick_chat_enabled is True
    assert app.shortcut_combo.isEnabled()
    assert app.set_chat_button.isEnabled()
    assert app.quick_chat_tray_action.isChecked()
    assert app.config["QuickChatNoteNotAsk"] is True
    app.sync_config()
    assert app.config["QuickChatEnabled"] is True

    app.shutdown()


def test_quick_chat_decline_reverts_switch(qtbot, tmp_path):
    dialog = FakeDialog(choices=["还没有"])
    app = make_app(tmp_path, config={"QuickChatEnabled": False}, dialog=dialog)
    qtbot.addWidget(app.window)

    app.set_quick_chat_enabled(True)

    assert app.quick_chat_enabled is False
    assert not app.quick_chat_switch.isChecked()
    assert not app.shortcut_combo.isEnabled()

    app.shutdown()


def test_sync_config_writes_existing_file_format(qtbot, tmp_path):
    app = make_app(
        tmp_path,
        config={"Locale": "zh_CN", "Process Name": "League of Legends.exe"},
        gui_config={"Theme": "light"},
    )
    qtbot.addWidget(app.window)

    app.on_shortcut_changed("Alt")
    app.sync_config()

    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "gui_config.json").exists()
    assert app.config["QuickChatShortcut"] == "Alt"

    app.shutdown()


def test_request_show_emits_to_main_thread(qtbot, tmp_path):
    app = make_app(tmp_path)
    qtbot.addWidget(app.window)
    app.window.hide()

    app.request_show()
    qtbot.waitUntil(lambda: app.window.isVisible())

    assert app.window.windowState() & Qt.WindowMinimized == Qt.WindowState(0)

    app.shutdown()
