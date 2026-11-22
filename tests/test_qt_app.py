import stat

from PySide6.QtCore import QEventLoop, Qt, QTimer

from core.config import read_yaml
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


def test_launching_for_tft_keeps_lol_unchanged_and_restarts_watchers(qtbot, tmp_path, riot_metadata, mocker):
    lol = riot_metadata("league_of_legends.live")
    app = make_app(tmp_path, config={"Locale": "zh_CN"})
    qtbot.addWidget(app.window)
    assert app.target_combo.currentData() == ""
    app.target_combo.setCurrentIndex(app.target_combo.findData("teamfighttactics"))
    tft_live = riot_metadata("teamfighttactics.live")
    tft_pbe = riot_metadata("teamfighttactics.pbe")
    tft_pbe.chmod(stat.S_IREAD)
    first, second = mocker.Mock(), mocker.Mock()
    mocker.patch("ui_qt.app.Observer", side_effect=[first, second])
    launch = mocker.patch("ui_qt.app.start_game", return_value=None)
    minimize = mocker.patch.object(app, "minimize_window")

    try:
        app.launch_button.click()
        app.launch_button.click()

        assert read_yaml(lol)["settings"]["locale"] == "en_US"
        assert read_yaml(tft_pbe)["settings"]["locale"] == "en_US"
        assert read_yaml(tft_live)["settings"]["locale"] == "zh_CN"
        assert launch.call_count == 2
        first.stop.assert_called_once()
        first.join.assert_called_once()
        assert second.schedule.call_args.kwargs["path"] == str(tft_live.parent)
        assert "1 个成功，1 个失败" in app.window.statusBar().currentMessage()
        assert "请手动打开 Riot Client" in app.window.statusBar().currentMessage()
        minimize.assert_not_called()
    finally:
        tft_pbe.chmod(stat.S_IREAD | stat.S_IWRITE)
        app.shutdown()

    assert app.config["LanguageTarget"] == "teamfighttactics"
    assert app.config["SettingFile"] == []


def test_automatic_start_runs_during_qt_event_loop(qtbot, tmp_path, mocker):
    app = make_app(tmp_path, config={"StartGameDirectly": True})
    qtbot.addWidget(app.window)
    loop = QEventLoop()
    ran_during_event_loop = []

    def start():
        ran_during_event_loop.append(loop.isRunning())
        loop.quit()

    mocker.patch.object(app.qt_app, "exec", side_effect=loop.exec)
    mocker.patch.object(app, "start", side_effect=start)
    QTimer.singleShot(250, loop.quit)
    app.run()

    assert ran_during_event_loop == [True]
    app.shutdown()
