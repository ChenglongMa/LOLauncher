import os
import threading
import time
from collections.abc import Iterable

import keyboard

from core.constants import COMMENT_PREFIX, DEFAULT_QUICK_CHATS, QUICK_CHAT_FILENAME
from core.platform import bring_to_foreground, is_foreground_window, send_text


def parse_quick_chat_lines(lines: Iterable[str]) -> list[str]:
    chats: list[str] = []
    for line in lines:
        value = line.strip()
        if value and not value.startswith(COMMENT_PREFIX):
            chats.append(value)
    return chats


def read_quick_chat_file(file_path: str = QUICK_CHAT_FILENAME) -> list[str]:
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as file:
        return parse_quick_chat_lines(file)


def create_quick_chat_file(config_filename: str) -> str:
    directory = config_filename if os.path.isdir(config_filename) else os.path.dirname(config_filename)
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, "quick_chat.txt")
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(f"{COMMENT_PREFIX} 设置快速聊天消息，一行一个\n")
            file.write(f'{COMMENT_PREFIX} 以 "{COMMENT_PREFIX}" 开头的行将被忽略\n')
            file.write(f"{COMMENT_PREFIX} 编辑完成后记得保存 :)\n\n")
            file.writelines("\n".join(DEFAULT_QUICK_CHATS))
    return file_path


def send_text_to_lol_chat(text: str, lock: threading.Lock, pid: int | None = None) -> None:
    with lock:
        if not pid:
            print("No pid provided, program is not running.")
            return
        is_foreground = False
        for _ in range(5):
            is_foreground = is_foreground_window(pid)
            if is_foreground:
                break
            bring_to_foreground(pid)
            time.sleep(0.1)

        if not is_foreground:
            print("Program is not in foreground.")
            return

        print(f"Sending text to pid {pid}")
        send_text(text, keyboard)

