import ast
from pathlib import Path

from core.config import build_app_config, build_gui_config
from core.launcher import choose_game_client
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
