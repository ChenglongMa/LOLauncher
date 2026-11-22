import ast
from pathlib import Path

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileMovedEvent

from core.config import (
    backup_file,
    build_app_config,
    build_gui_config,
    detect_metadata_file,
    read_yaml,
    update_settings,
    verify_metadata_file,
)
from core.launcher import FileWatcher, choose_game_client, start_game
from core.quick_chat import create_quick_chat_file, parse_quick_chat_lines, read_quick_chat_file
from core.updates import is_newer_version
from conftest import FakeDialog


def test_parse_quick_chat_lines_filters_comments_and_blank_lines():
    assert parse_quick_chat_lines(["# comment", " Hello ", "", "  /all gg  "]) == ["Hello", "/all gg"]


def test_create_quick_chat_file_writes_default_messages(tmp_path):
    config_path = tmp_path / "config.json"
    quick_chat_path = create_quick_chat_file(str(config_path))

    assert Path(quick_chat_path).exists()
    assert "Hello!" in read_quick_chat_file(quick_chat_path)


def test_build_app_config_preserves_format_and_user_values():
    config = build_app_config(
        existing_config={"Process Name": "League.exe", "Other": "kept"},
        setting_files=["settings.yaml"],
        game_client="RiotClientServices.exe",
        selected_locale="en_US",
        minimize_on_closing=True,
        start_game_directly=False,
        quick_chat_enabled=True,
        quick_chat_shortcut="Alt",
        quick_chat_user_config={"QuickChatNoteNotAsk": True},
    )

    assert config["SettingFile"] == ["settings.yaml"]
    assert config["Locale"] == "en_US"
    assert config["Process Name"] == "League.exe"
    assert config["QuickChatNoteNotAsk"] is True
    assert config["Other"] == "kept"


def test_build_gui_config_keeps_existing_geometry():
    config = build_gui_config(existing_config={"QuickChatX": 42}, theme="dark", quick_chat_ui_config={"QuickChatWidth": 300})

    assert config == {"QuickChatX": 42, "Theme": "dark", "QuickChatWidth": 300}


def test_choose_game_client_prompts_when_multiple_existing_paths(tmp_path):
    client_a = tmp_path / "RiotClientServices-a.exe"
    client_b = tmp_path / "RiotClientServices-b.exe"
    client_a.write_text("", encoding="utf-8")
    client_b.write_text("", encoding="utf-8")
    dialog = FakeDialog(choices=[str(client_b)])

    selected = choose_game_client([str(client_a), str(client_b)], tuple(), dialog)

    assert selected == str(client_b)


def test_standalone_tft_and_lol_detection_supports_live_pbe_and_legacy_paths(tmp_path, riot_metadata):
    tft_live = riot_metadata("teamfighttactics.live")
    assert detect_metadata_file() == [str(tft_live)]

    lol_live = riot_metadata("league_of_legends.live")
    lol_pbe = riot_metadata("league_of_legends.pbe")
    tft_pbe = riot_metadata("teamfighttactics.pbe")
    riot_metadata("valorant.live")
    manual = tmp_path / "manual.yaml"
    manual.write_bytes(tft_live.read_bytes())
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("settings:\n    locale: [en_US]\n", encoding="utf-8")

    assert detect_metadata_file(str(manual)) == [str(path) for path in (lol_live, lol_pbe, tft_live, tft_pbe, manual)]
    assert detect_metadata_file([str(tft_live), str(invalid)]) == [str(path) for path in (lol_live, lol_pbe, tft_live, tft_pbe)]
    assert detect_metadata_file([str(tft_live), None, "", 42, str(invalid)], "teamfighttactics") == [
        str(tft_live), str(tft_pbe),
    ]
    assert detect_metadata_file(product="league_of_legends") == [str(lol_live), str(lol_pbe)]


def test_detection_preserves_the_other_drive_fallback(tmp_path, riot_metadata, monkeypatch):
    drive = tmp_path / "legacy-drive"
    installation = "league_of_legends.pbe"
    legacy = drive / "ProgramData" / "Riot Games" / "Metadata" / installation / f"{installation}.product_settings.yaml"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("settings:\n    locale: en_US\n", encoding="utf-8")
    monkeypatch.setattr("core.config.get_drives", lambda: [str(drive)])

    assert detect_metadata_file() == [str(legacy)]


def test_first_manual_selection_is_persisted_and_matches_tft_target(tmp_path, riot_metadata):
    manual = tmp_path / "teamfighttactics.live.product_settings.yaml"
    manual.write_text("settings:\n    locale: en_US\n", encoding="utf-8")
    config = {}
    dialog = FakeDialog(choices=["手动选择"], file_path=str(manual))

    assert verify_metadata_file(config, dialog) == [str(manual)]
    assert config["SettingFile"] == [str(manual)]
    assert detect_metadata_file(config["SettingFile"], "teamfighttactics") == [str(manual)]


def test_update_keeps_yaml_comments_and_noops_when_locale_is_already_set(riot_metadata):
    path = riot_metadata("teamfighttactics.live")
    original = path.read_bytes()
    backup = path.with_name(f"{path.name}.bak")

    assert update_settings(path, "zh_CN")["settings"]["locale"] == "zh_CN"
    assert 'locale: "zh_CN"  # Riot language' in path.read_text(encoding="utf-8")
    assert read_yaml(path)["settings"]["other_setting"] is True
    assert backup.read_bytes() == original

    modified_time = path.stat().st_mtime_ns
    assert update_settings(path, "zh_CN") is not None
    assert path.stat().st_mtime_ns == modified_time
    assert backup.read_bytes() == original


def test_failed_replace_keeps_original_and_backup(riot_metadata, mocker):
    path = riot_metadata("teamfighttactics.live")
    original = path.read_bytes()
    mocker.patch("core.config.os.replace", side_effect=PermissionError("Riot is using the file"))

    assert update_settings(path, "zh_CN") is None
    assert path.read_bytes() == original
    assert path.with_name(f"{path.name}.bak").read_bytes() == original
    assert not list(path.parent.glob("*.tmp"))


def test_update_leaves_a_concurrent_riot_edit_intact(riot_metadata, mocker):
    path = riot_metadata("teamfighttactics.live")
    newer = "settings:\n    locale: ja_JP\n    new_setting_from_riot: true\n"

    def concurrent_update(file):
        backup_file(file)
        path.write_text(newer, encoding="utf-8")

    mocker.patch("core.config.backup_file", side_effect=concurrent_update)

    assert update_settings(path, "zh_CN") is None
    assert path.read_text(encoding="utf-8") == newer
    assert not list(path.parent.glob("*.tmp"))


def test_watcher_corrects_modified_created_and_replaced_tft_settings(riot_metadata):
    path = riot_metadata("teamfighttactics.pbe")
    other = path.with_name("unrelated.yaml")
    other.write_bytes(path.read_bytes())
    watcher = FileWatcher(str(path), selected_locale="zh_CN")

    for event in (
        FileModifiedEvent(str(path)), FileCreatedEvent(str(path)),
        FileMovedEvent(str(path.with_name("new.tmp")), str(path)),
    ):
        riot_metadata("teamfighttactics.pbe")
        watcher.dispatch(event)
        assert read_yaml(path)["settings"]["locale"] == "zh_CN"

    watcher.dispatch(FileModifiedEvent(str(other)))
    assert read_yaml(other)["settings"]["locale"] == "en_US"


def test_start_game_falls_back_to_registered_riot_client(tmp_path, mocker):
    client = tmp_path / "RiotClientServices.exe"
    client.touch()
    mocker.patch("core.launcher.read_json", return_value={"rc_default": str(client)})
    launch = mocker.patch("core.launcher.launch_explorer")

    assert start_game(None, ({"product_install_root": []}, {}), FakeDialog()) == str(client)
    launch.assert_called_once_with(str(client))


def test_version_comparison_uses_numeric_parts():
    assert is_newer_version("v1.10.0", "1.2.9")
    assert not is_newer_version("v1.2.0", "1.2.0")


def test_core_modules_do_not_import_gui_frameworks():
    forbidden = {"tkinter", "easygui", "PySide6", "qfluentwidgets", "pystray"}
    for path in Path("src/core").glob("*.py"):
        module = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert not (imports & forbidden), f"{path} imports GUI modules: {imports & forbidden}"


def test_entrypoint_uses_qt_ui_not_legacy_tk():
    main_source = Path("src/main.py").read_text(encoding="utf-8")

    assert "from ui_qt.app import App" in main_source
    assert "from ui.app import App" not in main_source
