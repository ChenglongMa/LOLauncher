import ctypes
import json
import os
import shutil
import stat
import string
import sys
import webbrowser
from contextlib import contextmanager
from tkinter import filedialog

import easygui
import yaml
from github import Github
from watchdog.events import FileSystemEventHandler

VERSION = '1.0.2'
APP_NAME = 'LOLauncher'
REPO_NAME = 'ChenglongMa/LOLauncher'
DEFAULT_METADATA_DIR = r"C:\ProgramData\Riot Games\Metadata\league_of_legends.live\league_of_legends.live.product_settings.yaml"
DEFAULT_METADATA_FILE = f"{DEFAULT_METADATA_DIR}\\league_of_legends.live.product_settings.yaml"

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


class FileWatcher(FileSystemEventHandler):

    def __init__(self, file_path, selected_locale, msg_callback_fn=None):
        self.file_path = file_path
        self.selected_locale = selected_locale
        self.msg_callback_fn = msg_callback_fn
        super().__init__()

    def on_modified(self, event):
        if event.src_path == self.file_path:
            content = read_yaml(event.src_path)
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


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def open_repo_page():
    webbrowser.open(f"https://github.com/{REPO_NAME}")


def open_my_homepage():
    webbrowser.open("https://chenglongma.com")


def read_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


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


def filter_existing_files(file_paths):
    return list(set(filter(os.path.exists, file_paths)))


def filter_valid_metadata_files(filenames):
    return list(filter(is_valid_metadata_file, filenames))


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
        selected_file = open_metadata_file_dialog(title="请选择 league_of_legends.live.product_settings.yaml 文件",
                                                  file_types=[('Riot 配置文件', '*.yaml'), ('所有文件', '*.*')],
                                                  initial_dir=DEFAULT_METADATA_DIR, initial_file=DEFAULT_METADATA_FILE)
        if selected_file:
            return [selected_file]
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
    filename_suffix = r"ProgramData\Riot Games\Metadata\league_of_legends.live\league_of_legends.live.product_settings.yaml"
    for drive in get_drives():
        filename = os.path.join(drive, filename_suffix)
        if is_valid_metadata_file(filename):
            print(f"Found metadata file: {filename}")
            setting_files.append(filename)
    return setting_files


def verify_metadata_file(config) -> str:
    setting_files = filter_valid_metadata_files(to_list(config.get('SettingFile', [])))
    if not setting_files or len(setting_files) < 1:
        print("开始尝试自动查找配置文件...")
        setting_files = detect_metadata_file()
        if not setting_files or len(setting_files) < 1:
            decision = easygui.buttonbox("该文件通常位于：\n\n"
                                         r"[系统盘]:\ProgramData\Riot Games\Metadata\league_of_legends.live"
                                         r"\league_of_legends.live.product_settings.yaml",
                                         "未找到配置文件，请手动选择", ["手动选择", "退出"])
            if decision.lower() == '手动选择':
                setting_files = find_setting_files()
            else:
                sys.exit()
    if len(setting_files) > 1:
        msg = "请从以下选项中选择一个配置文件"
        title = "找到多个配置文件，请选择一个"
        choice = easygui.choicebox(msg, title, setting_files)
        setting_files = [choice]
    if not is_valid_metadata_file(setting_files[0]):
        decision = easygui.buttonbox("该文件通常位于："
                                     r"[系统盘]:\ProgramData\Riot Games\Metadata\league_of_legends.live"
                                     r"\league_of_legends.live.product_settings.yaml",
                                     "无效的配置文件，请重新选择", ["重新选择", "退出"])
        if decision.lower() == '重新选择':
            setting_files = find_setting_files()
        else:
            sys.exit()
    return setting_files[0]


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
        write_yaml(setting_file, setting_content)
        msg_callback_fn(f"更新设置文件成功!")
        return setting_content
    except Exception as e:
        msg_callback_fn(f"更新设置文件失败: {setting_file}, error: {e}")
