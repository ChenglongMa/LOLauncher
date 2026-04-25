import json
import os
import shutil
import stat
from contextlib import contextmanager
from typing import Any

from ruamel.yaml import YAML

from core.constants import (
    CONFIG_DIR,
    DEFAULT_METADATA_DIR,
    DEFAULT_METADATA_FILE,
    GAME_NAMES,
    LOCALE_CODES,
    METADATA_DIR_FORMAT,
    METADATA_FILE_FORMAT,
    QUICK_CHAT_DOC,
    SUPPORTED_PATCH_LINES,
)
from core.dialogs import DialogService
from core.platform import get_drives

yaml = YAML()
yaml.preserve_quotes = True
yaml.indent(mapping=4, sequence=2, offset=0)


def ensure_config_dir() -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)


def read_json(file_path: str) -> dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"Error reading {file_path}: {exc}")
        return {}


def write_json(file_path: str, data: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def read_yaml(file_path: str) -> Any:
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return yaml.load(file)
    except Exception as exc:
        print(f"Error reading {file_path}: {exc}")
        return None


def write_yaml(file_path: str, data: Any) -> None:
    with open(file_path, "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def normalize_file_path(file_path: str) -> str:
    file_path = os.path.abspath(file_path)
    file_path = os.path.realpath(file_path)
    return os.path.normpath(file_path)


def to_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    return [data]


def filter_existing_files(file_paths: Any) -> list[str]:
    return list(set(filter(os.path.exists, map(normalize_file_path, to_list(file_paths)))))


def is_valid_settings(settings: Any) -> bool:
    return settings is not None and "settings" in settings and "locale_data" in settings


def is_valid_metadata_file(filename: str | None) -> bool:
    if not filename or not os.path.exists(filename):
        return False
    return is_valid_settings(read_yaml(filename))


def filter_valid_metadata_files(*file_paths: str) -> list[str]:
    return list(set(filter(is_valid_metadata_file, map(normalize_file_path, file_paths))))


def metadata_suffixes() -> list[str]:
    return [
        os.path.join(
            METADATA_DIR_FORMAT.format(
                drive="",
                game_name=GAME_NAMES["League of Legends"],
                patch_line=patch_line,
            ),
            METADATA_FILE_FORMAT.format(
                game_name=GAME_NAMES["League of Legends"],
                patch_line=patch_line,
            ),
        )
        for patch_line in SUPPORTED_PATCH_LINES
    ]


def detect_metadata_file() -> list[str]:
    print("Detecting metadata file...")
    setting_files: list[str] = []
    for drive in get_drives():
        for filename_suffix in metadata_suffixes():
            filename = os.path.join(drive, filename_suffix)
            if is_valid_metadata_file(filename):
                print(f"Found metadata file: {filename}")
                setting_files.append(filename)
    return setting_files


def open_metadata_file_dialog(dialog: DialogService, title: str) -> str | None:
    selected_file = dialog.select_file(
        title=title,
        file_types=[("Riot 配置文件", "*.yaml"), ("所有文件", "*.*")],
        initial_dir=DEFAULT_METADATA_DIR,
        initial_file=os.path.basename(DEFAULT_METADATA_FILE),
    )
    return selected_file if is_valid_metadata_file(selected_file) else None


def find_setting_files(dialog: DialogService) -> list[str]:
    while True:
        selected_file = open_metadata_file_dialog(
            dialog,
            "请选择 league_of_legends.[live|pbe].product_settings.yaml 文件",
        )
        selected_files = filter_valid_metadata_files(*to_list(selected_file))
        if selected_files:
            return selected_files

        decision = dialog.choose("您选择了无效文件", "您要重新选择文件，还是退出？\n", ["重新选择", "退出"])
        if decision == "重新选择":
            continue
        raise SystemExit(0)


def verify_metadata_file(config: dict[str, Any], dialog: DialogService) -> list[str]:
    setting_files = detect_metadata_file()
    setting_files = filter_valid_metadata_files(*to_list(config.get("SettingFile", [])), *setting_files)
    if setting_files:
        return setting_files

    decision = dialog.choose(
        "未找到配置文件，请手动选择",
        "该文件通常位于：\n\n"
        rf"[系统盘]:{DEFAULT_METADATA_DIR}"
        rf"{DEFAULT_METADATA_FILE}",
        ["手动选择", "退出"],
    )
    if decision == "手动选择":
        return find_setting_files(dialog)
    raise SystemExit(0)


@contextmanager
def write_permission(file_path: str):
    try:
        os.chmod(file_path, stat.S_IWRITE)
        yield
    finally:
        os.chmod(file_path, stat.S_IREAD)


def backup_file(file_path: str) -> None:
    shutil.copyfile(file_path, file_path + ".bak")


def is_read_only(file_path: str) -> bool:
    file_stat = os.stat(file_path)
    return not bool(file_stat.st_mode & stat.S_IWRITE)


def update_settings(setting_file: str, selected_locale: str, msg_callback_fn=None):
    msg_callback_fn = msg_callback_fn or print
    try:
        setting_content = read_yaml(setting_file)
        if not is_valid_settings(setting_content):
            msg_callback_fn(f"无效文件: {setting_file}")
            return None

        current_locale = setting_content["settings"]["locale"]
        if current_locale == selected_locale:
            msg_callback_fn(f"语言设置已是 {selected_locale}，无需更新配置文件")
            return setting_content

        msg_callback_fn("正在备份文件...")
        backup_file(setting_file)
        setting_content["settings"]["locale"] = selected_locale
        if is_read_only(setting_file):
            msg_callback_fn(f"文件只读，无法更新: {setting_file}")
            return setting_content
        write_yaml(setting_file, setting_content)
        msg_callback_fn("更新设置文件成功!")
        return setting_content
    except Exception as exc:
        msg_callback_fn(f"更新设置文件失败: {setting_file}, error: {exc}")
        return None


def build_app_config(
    *,
    existing_config: dict[str, Any],
    setting_files: list[str],
    game_client: str,
    selected_locale: str,
    minimize_on_closing: bool,
    start_game_directly: bool,
    quick_chat_enabled: bool,
    quick_chat_shortcut: str,
    quick_chat_user_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = dict(existing_config)
    config.update(
        {
            "@注意": r"请使用\或/做为路径分隔符，如 C:\ProgramData 或 C:/ProgramData",
            "@SettingFile": "请在下方填写 league_of_legends.live.product_settings.yaml 文件路径",
            "SettingFile": setting_files,
            "@GameClient": "请在下方填写 RiotClientServices.exe 文件路径",
            "GameClient": game_client,
            "Locale": selected_locale if selected_locale in LOCALE_CODES else "zh_CN",
            "MinimizeOnClosing": minimize_on_closing,
            "StartGameDirectly": start_game_directly,
            "Process Name": existing_config.get("Process Name", "League of Legends.exe"),
            "QuickChatEnabled": quick_chat_enabled,
            "QuickChatShortcut": quick_chat_shortcut,
            "QuickChatDoc": QUICK_CHAT_DOC,
        }
    )
    if quick_chat_user_config:
        config.update(quick_chat_user_config)
    return config


def build_gui_config(
    *,
    existing_config: dict[str, Any],
    theme: str,
    quick_chat_ui_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = dict(existing_config)
    config["Theme"] = theme
    if quick_chat_ui_config:
        config.update(quick_chat_ui_config)
    return config
