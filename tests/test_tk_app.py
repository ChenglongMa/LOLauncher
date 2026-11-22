import stat
import threading
import tkinter as tk
from tkinter import font

import pytest

from core.config import read_json, read_yaml
from core.constants import LOCALE_CODES
from core.platform import get_window_size
from ui.app import App
from conftest import FakeDialog


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display is unavailable: {error}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def make_app(tk_root, tmp_path, mocker):
    root = tk_root
    mocker.patch.object(App, "create_tray_app")
    app = None

    def create(config=None, gui_config=None, dialog=None):
        nonlocal app
        app = App(
            [],
            config or {},
            gui_config or {},
            root=root,
            dialog=dialog or FakeDialog(),
            config_filename=str(tmp_path / "config.json"),
            gui_config_filename=str(tmp_path / "gui_config.json"),
            quick_chat_filename=str(tmp_path / "quick_chat.txt"),
        )
        return app

    yield create
    try:
        if app is not None:
            app.shutdown()
    finally:
        root.withdraw()
        root.configure(menu="")
        for widget in root.winfo_children():
            widget.destroy()


def test_tk_app_initializes_controls(make_app):
    app = make_app(config={"Locale": "en_US", "LanguageTarget": "teamfighttactics"})

    assert app.root.title().startswith("LOLauncher")
    assert app.locale_dropdown.get() == LOCALE_CODES["en_US"]
    assert app.locale_dropdown.master.winfo_children() == [app.locale_dropdown]
    assert app.launch_button["text"] == "英雄联盟，启动！"
    assert not app.quick_chat_var.get()
    assert str(app.shortcut_dropdown["state"]) == "disabled"
    assert str(app.set_chat_button["state"]) == "disabled"


@pytest.mark.parametrize("scale", [1, 1.25, 1.5])
def test_initial_geometry_and_resize_at_display_scale(make_app, tk_root, mocker, scale):
    initial_scale = tk_root.tk.call("tk", "scaling")
    tk_root.tk.call("tk", "scaling", scale * 96 / 72)
    left, top, right, bottom = 40, 20, 1540, 980
    mocker.patch("ui.app.get_primary_work_area", return_value=(left, top, right, bottom))

    try:
        app = make_app()
        app.root.deiconify()
        app.root.update()
        width, height = round(350 * scale), round(420 * scale)
        max_width, max_height = round(400 * scale), round(470 * scale)
        assert font.nametofont("SunValleyBodyFont", root=app.root).cget("size") == -round(14 * scale)
        assert app.root.minsize() == (width, height)
        assert app.root.maxsize() == (max_width, max_height)
        frame_width, frame_height = get_window_size(int(app.root.wm_frame(), 0))
        x = left + (right - left - frame_width) // 2
        y = top + (bottom - top - frame_height) // 2
        assert app.root.geometry() == f"{width}x{height}+{x}+{y}"

        status = next(child for child in app.root.winfo_children() if child.winfo_class() == "TLabel")
        status_height = status.winfo_height()
        app.update_status("成功 3，失败 1 · 请手动打开 Riot Client")
        for window_width, window_height in [(max_width, max_height), (width, height)] * 4:
            app.root.geometry(f"{window_width}x{window_height}")
            app.root.update_idletasks()
            assert status.winfo_height() == status_height
            assert app.launch_button.winfo_viewable()
            assert app.set_chat_button.winfo_viewable()
            line = app.warning_label.dlineinfo("1.0")
            assert line is not None and line[0] + line[2] <= app.warning_label.winfo_width()
    finally:
        tk_root.tk.call("tk", "scaling", initial_scale)


def test_quick_chat_enable_updates_controls_and_tray(make_app, mocker):
    app = make_app(dialog=FakeDialog(choices=["已设置好，不要再提醒"]))
    set_hotkey = mocker.patch.object(app.quick_chat_dialog, "set_hotkey")

    app.set_quick_chat_enabled(True)

    assert app.quick_chat_var.get()
    assert str(app.shortcut_dropdown["state"]) == "readonly"
    assert str(app.set_chat_button["state"]) == "normal"
    assert app.config["QuickChatNoteNotAsk"] is True
    app.tray_app.update_menu.assert_called_once()
    set_hotkey.assert_called_once_with(app.shortcut_var.get())


def test_quick_chat_decline_reverts_switch(make_app):
    app = make_app(dialog=FakeDialog(choices=["还没有"]))
    app.quick_chat_var.set(True)

    app.set_quick_chat_enabled(True)

    assert not app.quick_chat_var.get()
    assert not app.quick_chat_enabled
    assert str(app.shortcut_dropdown["state"]) == "disabled"


def test_sync_config_preserves_saved_fields(make_app):
    app = make_app(
        config={"Locale": "zh_CN", "Process Name": "League.exe", "SettingFile": "manual.yaml"},
        gui_config={"Theme": "dark", "QuickChatX": 55, "QuickChatHeight": 220},
    )
    app.shortcut_var.set("Alt")
    app.sync_config()

    assert read_json(app.config_filename)["QuickChatShortcut"] == "Alt"
    assert read_json(app.config_filename)["Process Name"] == "League.exe"
    assert read_json(app.config_filename)["SettingFile"] == "manual.yaml"
    assert read_json(app.gui_config_filename) == {"Theme": "dark", "QuickChatX": 55, "QuickChatHeight": 220}


def test_show_request_from_worker_is_handled_by_tk_thread(make_app, mocker):
    app = make_app()
    current_thread = threading.current_thread()
    threads = []
    show = mocker.patch.object(app, "show_window", side_effect=lambda: threads.append(threading.current_thread()))
    worker = threading.Thread(target=app.request_show)
    worker.start()
    worker.join()

    show.assert_not_called()
    app.process_ui_events()
    show.assert_called_once()
    assert threads == [current_thread]


def test_launch_updates_both_games_and_restarts_watchers(make_app, riot_metadata, mocker):
    lol_live = riot_metadata("league_of_legends.live")
    lol_pbe = riot_metadata("league_of_legends.pbe")
    app = make_app(config={"Locale": "zh_CN", "LanguageTarget": "teamfighttactics"})
    tft_live = riot_metadata("teamfighttactics.live")
    tft_pbe = riot_metadata("teamfighttactics.pbe")
    tft_pbe.chmod(stat.S_IREAD)
    first = [mocker.Mock() for _ in range(3)]
    second = [mocker.Mock() for _ in range(3)]
    mocker.patch("ui.app.Observer", side_effect=first + second)
    launch = mocker.patch("ui.app.start_game", return_value=None)
    minimize = mocker.patch.object(app, "minimize_window")

    try:
        app.launch_button.invoke()
        app.launch_button.invoke()

        assert read_yaml(tft_pbe)["settings"]["locale"] == "en_US"
        for path in (lol_live, lol_pbe, tft_live):
            assert read_yaml(path)["settings"]["locale"] == "zh_CN"
        assert launch.call_count == 2
        for watcher in first:
            watcher.stop.assert_called_once()
            watcher.join.assert_called_once()
        assert second[-1].schedule.call_args.kwargs["path"] == str(tft_live.parent)
        assert "成功 3，失败 1" in app.status_var.get()
        assert "请手动打开 Riot Client" in app.status_var.get()
        minimize.assert_not_called()
    finally:
        tft_pbe.chmod(stat.S_IREAD | stat.S_IWRITE)

    app.sync_config()
    assert "LanguageTarget" not in app.config
    assert app.config["SettingFile"] == []


def test_automatic_start_is_scheduled_from_tk_event_loop(make_app, mocker):
    app = make_app(config={"StartGameDirectly": True})

    def start():
        app.root.quit()

    launch = mocker.patch.object(app, "start", side_effect=start)
    fallback = app.root.after(300, app.root.quit)
    app.run()
    app.root.after_cancel(fallback)

    launch.assert_called_once()
    assert app.closed
