import ctypes
import json
import locale
import os
import re
import shutil
import stat
import string
import subprocess
import sys
import time
import webbrowser
from contextlib import contextmanager
from ctypes import wintypes
from tkinter import filedialog

import easygui
import keyboard
import mouse
import yaml
from github import Github
from watchdog.events import FileSystemEventHandler

VERSION = '1.2.2'
APP_NAME = 'LOLauncher'
REPO_NAME = 'ChenglongMa/LOLauncher'
SUPPORTED_PATCH_LINEs = ['live', 'pbe']
DEFAULT_PATCH_LINE = 'live'
DEFAULT_DRIVE = r"C:"
# DEFAULT_METADATA_DIR = rf"{DEFAULT_DRIVE}\ProgramData\Riot Games\Metadata\league_of_legends.live"
# DEFAULT_METADATA_FILE = f"{DEFAULT_METADATA_DIR}\\league_of_legends.live.product_settings.yaml"
# PBE_METADATA_DIR = rf"{DEFAULT_DRIVE}\ProgramData\Riot Games\Metadata\league_of_legends.pbe"
# PBE_METADATA_FILE = f"{PBE_METADATA_DIR}\\league_of_legends.pbe.product_settings.yaml"
METADATA_DIR_FORMAT = r"{drive}\ProgramData\Riot Games\Metadata\league_of_legends.{patch_line}"
METADATA_FILE_FORMAT = "league_of_legends.{patch_line}.product_settings.yaml"
DEFAULT_METADATA_DIR = METADATA_DIR_FORMAT.format(drive=DEFAULT_DRIVE, patch_line=DEFAULT_PATCH_LINE)
DEFAULT_METADATA_FILE = os.path.join(DEFAULT_METADATA_DIR, METADATA_FILE_FORMAT.format(patch_line=DEFAULT_PATCH_LINE))

LOCALE_CODES = {
    "zh_CN": "简体中文（国服）",
    "zh_MY": "简体中文（马来西亚）",
    "zh_TW": "繁体中文",
    "en_US": "英语（美国）",
    "en_GB": "英语（英国）",
    "en_AU": "英语（澳大利亚）",
    "en_PH": "英语（菲律宾）",
    "en_SG": "英语（新加坡）",
    "ja_JP": "日语",
    "ko_KR": "韩语",
    "cs_CZ": "捷克语",
    "de_DE": "德语",
    "el_GR": "希腊语",
    "es_AR": "西班牙语（阿根廷）",
    "es_ES": "西班牙语（西班牙）",
    "es_MX": "西班牙语（墨西哥）",
    "fr_FR": "法语（法国）",
    "hu_HU": "匈牙利语",
    "it_IT": "意大利语",
    "pl_PL": "波兰语",
    "pt_BR": "葡萄牙语（巴西）",
    "ro_RO": "罗马尼亚语",
    "ru_RU": "俄语",
    "th_TH": "泰语",
    "tr_TR": "土耳其语",
    "vi_VN": "越南语",
}

COMMENT_PREFIX = "#"

DEFAULT_QUICK_CHATS = [
    "Hello!",
    "/all press d to see your latency",
    "/all glhf",
    "/all gg",
    "/muteself",
    "/mute all",
    "/remake",
]

HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".lolauncher")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILENAME = os.path.join(CONFIG_DIR, "config.json")
GUI_CONFIG_FILENAME = os.path.join(CONFIG_DIR, "gui_config.json")
QUICK_CHAT_FILENAME = os.path.join(CONFIG_DIR, "quick_chat.txt")
QUICK_CHAT_DOC = r"https://www.bilibili.com/read/cv35772066"


########################################################################################
class FileWatcher(FileSystemEventHandler):

    def __init__(self, *watching_files, selected_locale, msg_callback_fn=None):
        self.watching_files = filter_existing_files(watching_files)
        print(f"Watching files: {self.watching_files}")
        self.selected_locale = selected_locale
        self.msg_callback_fn = msg_callback_fn or print
        super().__init__()

    def on_modified(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')
        if normalize_file_path(event.src_path) in self.watching_files:
            print(f'File {event.src_path} has been modified')
            content = read_yaml(event.src_path)
            if not is_valid_settings(content):
                print(f"Invalid file: {event.src_path}")
                return
            curr_locale = content['settings']['locale']
            if curr_locale != self.selected_locale:
                self.msg_callback_fn(f'正在将语言 {curr_locale} 更新为 {self.selected_locale} ...')
                update_settings(event.src_path, self.selected_locale, self.msg_callback_fn)


@contextmanager
def write_permission(file_path):
    try:
        os.chmod(file_path, stat.S_IWRITE)
        yield
    finally:
        os.chmod(file_path, stat.S_IREAD)
        pass


def is_running(process_name):
    try:
        commands = ['tasklist', '/FI', f'ImageName eq {process_name}', '/FI', 'Status eq Running', '/FO', 'LIST']
        default_encoding = locale.getpreferredencoding()
        output = subprocess.check_output(commands, creationflags=subprocess.CREATE_NO_WINDOW).decode(default_encoding)
        match = re.search(r'PID:\s+(\d+)', output)
        if match:
            pid = int(match.group(1))
            return pid
    except Exception as e:
        print(f"Error checking if {process_name} is running: {e}")


def is_foreground_window(pid):
    foreground_window = ctypes.windll.user32.GetForegroundWindow()
    pid_foreground_window = wintypes.DWORD()
    ctypes.windll.user32.GetWindowThreadProcessId(foreground_window, ctypes.byref(pid_foreground_window))
    return pid_foreground_window.value == pid


def bring_to_foreground(pid):
    """
    Bring the window of the process to the front and simulate a mouse click
    :param pid: the process ID
    """

    def enum_windows_proc(hwnd, lparam):
        pid_window = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_window))
        if pid_window.value == pid:
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.SetFocus(hwnd)
            mouse.click()  # Assume pid is a full screen app
            return False  # stop enumerating windows
        return True  # continue enumerating windows

    enum_windows_proc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(enum_windows_proc)
    ctypes.windll.user32.EnumWindows(enum_windows_proc, 0)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def open_repo_page():
    webbrowser.open(f"https://github.com/{REPO_NAME}")


def open_my_homepage():
    webbrowser.open("https://chenglongma.com")


def open_web(url):
    webbrowser.open(url)


def read_json(file_path):
    try:
        if not os.path.exists(file_path):
            return {}
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return {}


def get_updates(repo_name, current_version):
    try:
        g = Github(retry=None)
        repo = g.get_repo(repo_name)

        latest_release = repo.get_latest_release()
        if latest_release.tag_name > current_version:
            return latest_release.tag_name, latest_release.html_url
    except Exception as e:
        pass

    return None, None


def check_for_updates(no_new_version_callback=None):
    new_version, html_url = get_updates(REPO_NAME, VERSION)

    if new_version:
        print(f"发现新版本: {new_version}\n{html_url}")
        decision = easygui.buttonbox(
            f"发现新版本: {new_version}\n您要更新吗？",
            "发现新版本",
            ["前往下载", "继续使用该版本"])
        if decision.lower() == "前往下载":
            print("前往下载...")
            webbrowser.open(html_url)
            sys.exit()
        else:
            print("继续使用该版本")
    else:
        no_new_version_callback = no_new_version_callback or print
        no_new_version_callback()


def normalize_file_path(file_path):
    file_path = os.path.abspath(file_path)
    file_path = os.path.realpath(file_path)
    file_path = os.path.normpath(file_path)
    return file_path


def filter_existing_files(file_paths):
    return list(set(filter(os.path.exists, map(normalize_file_path, file_paths))))


def filter_valid_metadata_files(*file_paths):
    return list(set(filter(is_valid_metadata_file, map(normalize_file_path, file_paths))))


def to_list(data):
    if isinstance(data, list):
        return data
    else:
        return [data]


def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter + ':\\')
        bitmask >>= 1

    return drives


def backup_file(file_path):
    shutil.copyfile(file_path, file_path + '.bak')


def restore_file(file_path):
    backup_file_path = file_path + ".bak"
    if os.path.exists(backup_file_path):
        os.remove(file_path)
        os.rename(backup_file_path, file_path)
        print(f"Restore file: {file_path}")
    else:
        print(f"Backup file not found: {backup_file_path}")


def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_yaml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return data
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def write_yaml(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def open_metadata_file_dialog(title, file_types, initial_dir=DEFAULT_METADATA_DIR, initial_file=DEFAULT_METADATA_FILE):
    selected_file = filedialog.askopenfilename(title=title, filetypes=file_types, initialdir=initial_dir, initialfile=initial_file)
    return selected_file if is_valid_metadata_file(selected_file) else None


def find_setting_files():
    while True:
        selected_file = open_metadata_file_dialog(title="请选择 league_of_legends.[live|pbe].product_settings.yaml 文件",
                                                  file_types=[('Riot 配置文件', '*.yaml'), ('所有文件', '*.*')],
                                                  initial_dir=DEFAULT_METADATA_DIR, initial_file=DEFAULT_METADATA_FILE)
        selected_files = filter_valid_metadata_files(*to_list(selected_file))
        if len(selected_files) > 0:
            return selected_files
        else:
            decision = easygui.buttonbox(
                "您要重新选择文件，还是退出？\n",
                "您选择了无效文件",
                ["重新选择", "退出"])
            if decision.lower() == '重新选择':
                continue
            elif decision.lower() == '退出':
                print("再见！")
                sys.exit()


def is_valid_settings(settings):
    return settings is not None and 'settings' in settings and 'locale_data' in settings


def is_valid_metadata_file(filename):
    if not os.path.exists(filename):
        return False
    settings = read_yaml(filename)
    return is_valid_settings(settings)


def detect_metadata_file():
    print("Detecting metadata file...")
    setting_files = []

    filename_suffixes = [os.path.join(
        METADATA_DIR_FORMAT.format(drive="", patch_line=patch_line),
        METADATA_FILE_FORMAT.format(patch_line=patch_line)
    ) for patch_line in SUPPORTED_PATCH_LINEs]
    for drive in get_drives():
        for filename_suffix in filename_suffixes:
            filename = os.path.join(drive, filename_suffix)
            if is_valid_metadata_file(filename):
                print(f"Found metadata file: {filename}")
                setting_files.append(filename)
    return setting_files


def verify_metadata_file(config) -> [str]:
    setting_files = detect_metadata_file()
    setting_files = filter_valid_metadata_files(*to_list(config.get('SettingFile', [])), *setting_files)
    if not setting_files or len(setting_files) < 1:
        decision = easygui.buttonbox("该文件通常位于：\n\n"
                                     rf"[系统盘]:{DEFAULT_METADATA_DIR}"
                                     rf"{DEFAULT_METADATA_FILE}",
                                     "未找到配置文件，请手动选择", ["手动选择", "退出"])
        if decision.lower() == '手动选择':
            setting_files = find_setting_files()
        else:
            sys.exit()
    return setting_files


def is_read_only(file_path):
    file_stat = os.stat(file_path)
    return not bool(file_stat.st_mode & stat.S_IWRITE)


def update_settings(setting_file, selected_locale, msg_callback_fn=None):
    msg_callback_fn = msg_callback_fn or print
    try:
        setting_content = read_yaml(setting_file)
        if not is_valid_settings(setting_content):
            msg_callback_fn(f"无效文件: {setting_file}")
            return
        current_locale = setting_content['settings']['locale']
        if current_locale != selected_locale:
            msg_callback_fn(f"正在备份文件...")
            backup_file(setting_file)
        setting_content['settings']['locale'] = selected_locale
        if is_read_only(setting_file):
            msg_callback_fn(f"文件只读，无法更新: {setting_file}")
            return setting_content
        write_yaml(setting_file, setting_content)
        msg_callback_fn(f"更新设置文件成功!")
        return setting_content
    except Exception as e:
        msg_callback_fn(f"更新设置文件失败: {setting_file}, error: {e}")


def create_quick_chat_file(config_filename):
    file_path = config_filename if os.path.isdir(config_filename) else os.path.dirname(config_filename)

    file_path = os.path.join(file_path, 'quick_chat.txt')
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f'{COMMENT_PREFIX} 设置快速聊天消息，一行一个\n')
            f.write(f'{COMMENT_PREFIX} 以 "{COMMENT_PREFIX}" 开头的行将被忽略\n')
            f.write(f'{COMMENT_PREFIX} 编辑完成后记得保存 :)\n\n')
            f.writelines("\n".join(DEFAULT_QUICK_CHATS))


def go_to_previous_window():
    # Get a handle to the foreground window
    foreground_window = ctypes.windll.user32.GetForegroundWindow()

    # Get a handle to the next window in the Z order
    next_window = ctypes.windll.user32.GetWindow(foreground_window, 2)

    # Bring the next window to the foreground
    ctypes.windll.user32.SetForegroundWindow(next_window)


def send_text(text):
    keyboard.send('enter')
    time.sleep(0.05)
    keyboard.write(text)
    keyboard.send('enter')
