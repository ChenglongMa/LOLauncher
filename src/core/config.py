import json
import os
import shutil
import stat
from collections.abc import Iterable
from tempfile import NamedTemporaryFile
from typing import Any

from ruamel.yaml import YAML

from core.constants import (
    CONFIG_DIR,
    DEFAULT_METADATA_DIR,
    LANGUAGE_TARGETS,
    LOCALE_CODES,
    METADATA_RELATIVE_DIR,
    PRODUCT_SETTINGS_SUFFIX,
    QUICK_CHAT_DOC,
    SUPPORTED_PATCH_LINES,
)
from core.dialogs import DialogService
from core.platform import get_drives


def settings_yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=4, sequence=2, offset=0)
    return yaml


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
            return settings_yaml().load(file)
    except Exception as exc:
        print(f"Error reading {file_path}: {exc}")
        return None


def write_yaml(file_path: str, data: Any, original: os.stat_result) -> None:
    temp_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".tmp", delete=False,
            dir=os.path.dirname(os.path.abspath(file_path)),
        ) as file:
            temp_path = file.name
            settings_yaml().dump(data, file)
        current = os.stat(file_path)
        if (not os.path.samestat(original, current)
                or original.st_mtime_ns != current.st_mtime_ns
                or original.st_size != current.st_size):
            raise OSError(f"配置文件在更新期间发生变化: {file_path}")
        os.replace(temp_path, file_path)
        temp_path = None
    finally:
        if temp_path is not None:
            os.remove(temp_path)


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


def filter_existing_files(file_paths: Iterable[object]) -> list[str]:
    files = {}
    for path in file_paths:
        if isinstance(path, (str, os.PathLike)) and path and os.path.isfile(path):
            normalized = normalize_file_path(path)
            files.setdefault(os.path.normcase(normalized), normalized)
    return list(files.values())


def is_valid_settings(settings: Any) -> bool:
    locale_settings = settings.get("settings") if isinstance(settings, dict) else None
    return isinstance(locale_settings, dict) and isinstance(locale_settings.get("locale"), str)


def is_valid_metadata_file(filename: str | None) -> bool:
    if not filename or not os.path.isfile(filename):
        return False
    return is_valid_settings(read_yaml(filename))


def detect_metadata_file(configured_files: Any = None, product: str = "") -> list[str]:
    installations = {
        f"{game}.{patch_line}{PRODUCT_SETTINGS_SUFFIX}": f"{game}.{patch_line}"
        for game in LANGUAGE_TARGETS if game and (not product or game == product)
        for patch_line in SUPPORTED_PATCH_LINES
    }
    metadata_dirs = [DEFAULT_METADATA_DIR, *(os.path.join(drive, METADATA_RELATIVE_DIR) for drive in get_drives())]
    candidates = [
        os.path.join(directory, installation, filename)
        for directory in metadata_dirs
        for filename, installation in installations.items()
    ]
    for path in to_list(configured_files):
        if isinstance(path, (str, os.PathLike)) and (not product or os.path.basename(path).lower() in installations):
            candidates.append(path)
    return [path for path in filter_existing_files(candidates) if is_valid_metadata_file(path)]


def open_metadata_file_dialog(dialog: DialogService) -> str | None:
    selected_file = dialog.select_file(
        title="请选择 Riot 游戏的 product_settings.yaml 文件",
        file_types=[("Riot 游戏配置文件", f"*{PRODUCT_SETTINGS_SUFFIX}"), ("YAML 文件", "*.yaml"), ("所有文件", "*.*")],
        initial_dir=DEFAULT_METADATA_DIR,
    )
    return selected_file if is_valid_metadata_file(selected_file) else None


def find_setting_files(dialog: DialogService) -> list[str]:
    while True:
        selected_file = open_metadata_file_dialog(dialog)
        if selected_file:
            return [selected_file]

        decision = dialog.choose("您选择了无效文件", "您要重新选择文件，还是退出？\n", ["重新选择", "退出"])
        if decision == "重新选择":
            continue
        raise SystemExit(0)


def verify_metadata_file(config: dict[str, Any], dialog: DialogService) -> list[str]:
    setting_files = detect_metadata_file(config.get("SettingFile"))
    if setting_files:
        return setting_files

    decision = dialog.choose(
        "未找到配置文件，请手动选择",
        f"游戏配置文件通常位于：\n\n{DEFAULT_METADATA_DIR}",
        ["手动选择", "退出"],
    )
    if decision == "手动选择":
        setting_files = find_setting_files(dialog)
        config["SettingFile"] = setting_files
        return setting_files
    raise SystemExit(0)


def backup_file(file_path: str) -> None:
    shutil.copyfile(file_path, f"{file_path}.bak")


def update_settings(setting_file: str, selected_locale: str, msg_callback_fn=None):
    msg_callback_fn = msg_callback_fn or print
    try:
        original = os.stat(setting_file)
        setting_content = read_yaml(setting_file)
        if not is_valid_settings(setting_content):
            msg_callback_fn(f"无效文件: {setting_file}")
            return None

        if setting_content["settings"]["locale"] == selected_locale:
            return setting_content

        if not (original.st_mode & stat.S_IWRITE):
            msg_callback_fn(f"文件只读，无法更新: {setting_file}")
            return None
        backup_file(setting_file)
        setting_content["settings"]["locale"] = selected_locale
        write_yaml(setting_file, setting_content, original)
        msg_callback_fn(f"已更新语言配置: {setting_file}")
        return setting_content
    except Exception as exc:
        msg_callback_fn(f"更新设置文件失败: {setting_file}, error: {exc}")
        return None


def build_app_config(
    *,
    existing_config: dict[str, Any],
    setting_files: str | list[str],
    game_client: str | list[str],
    selected_locale: str,
    minimize_on_closing: bool,
    start_game_directly: bool,
    quick_chat_enabled: bool,
    quick_chat_shortcut: str,
    quick_chat_user_config: dict[str, Any] | None = None,
    language_target: str = "",
) -> dict[str, Any]:
    config = dict(existing_config)
    config.update(
        {
            "@注意": r"请使用\或/做为路径分隔符，如 C:\ProgramData 或 C:/ProgramData",
            "@SettingFile": "可填写需要补充的 Riot 游戏 product_settings.yaml 文件路径",
            "SettingFile": setting_files,
            "@GameClient": "请在下方填写 RiotClientServices.exe 文件路径",
            "GameClient": game_client,
            "Locale": selected_locale if selected_locale in LOCALE_CODES else "zh_CN",
            "LanguageTarget": language_target,
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
