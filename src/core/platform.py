import ctypes
import locale
import os
import re
import socket
import string
import subprocess
import threading
import time
import webbrowser
from ctypes import wintypes
from typing import Callable

import mouse

from core.constants import HOST, PORT


def get_drives() -> list[str]:
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter + ":\\")
        bitmask >>= 1
    return drives


def is_running(process_name: str) -> int | None:
    try:
        commands = ["tasklist", "/FI", f"ImageName eq {process_name}", "/FI", "Status eq Running", "/FO", "LIST"]
        default_encoding = locale.getpreferredencoding()
        output = subprocess.check_output(commands, creationflags=subprocess.CREATE_NO_WINDOW).decode(default_encoding)
        match = re.search(r"PID:\s+(\d+)", output)
        if match:
            return int(match.group(1))
    except Exception as exc:
        print(f"Error checking if {process_name} is running: {exc}")
    return None


def is_foreground_window(pid: int) -> bool:
    foreground_window = ctypes.windll.user32.GetForegroundWindow()
    pid_foreground_window = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(foreground_window, ctypes.byref(pid_foreground_window))
    return pid_foreground_window.value == pid


def bring_to_foreground(pid: int) -> None:
    def enum_windows_proc(hwnd, lparam):
        pid_window = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_window))
        if pid_window.value == pid:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.SetFocus(hwnd)
            mouse.click()
            return False
        return True

    callback = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_windows_proc)
    ctypes.windll.user32.EnumWindows(callback, 0)


def open_web(url: str) -> None:
    webbrowser.open(url)


def open_repo_page(repo_name: str) -> None:
    webbrowser.open(f"https://github.com/{repo_name}")


def open_homepage() -> None:
    webbrowser.open("https://chenglongma.com")


def show_existing_instance() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=1) as conn:
            conn.sendall(b"SHOW_YOURSELF\n")
            print("Another instance is running, message sent.")
        return True
    except Exception:
        return False


def start_server(on_message_callback: Callable[[str], None]) -> threading.Thread:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    def handle_client(conn, addr):
        with conn:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                message = data.decode("utf-8").strip()
                on_message_callback(message)

    def listen_loop():
        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

    thread = threading.Thread(target=listen_loop, daemon=True)
    thread.start()
    return thread


def singleton(mutex_name: str = "LOLauncher") -> bool:
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        return False
    return True


def launch_explorer(path: str) -> None:
    subprocess.run(["explorer.exe", os.path.normpath(path)], check=False)


def send_text(text: str, keyboard_module) -> None:
    keyboard_module.send("enter")
    time.sleep(0.05)
    keyboard_module.write(text)
    keyboard_module.send("enter")

