import ctypes
import json
import os
import stat
import string
import subprocess
import sys
import time
import webbrowser
from contextlib import contextmanager

import easygui
import yaml
from github import Github


def check_for_updates(_repo_name, _current_version):
    try:
        g = Github()
        repo = g.get_repo(_repo_name)

        latest_release = repo.get_latest_release()
        if latest_release.tag_name > _current_version:
            return latest_release.tag_name, latest_release.html_url
    except:
        pass

    return None, None


def get_drives():
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(letter + ':\\')
        bitmask >>= 1

    return drives


def backup_file(file_path):
    backup_file_path = file_path + ".bak"
    if os.path.exists(backup_file_path):
        os.remove(backup_file_path)
    os.rename(file_path, backup_file_path)
    print(f"Backup file: {backup_file_path}")


def restore_file(file_path):
    backup_file_path = file_path + ".bak"
    if os.path.exists(backup_file_path):
        os.remove(file_path)
        os.rename(backup_file_path, file_path)
        print(f"Restore file: {file_path}")
    else:
        print(f"Backup file not found: {backup_file_path}")


def read_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_yaml(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return data


def write_yaml(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def filter_existing_files(file_paths):
    return list(set(filter(os.path.exists, file_paths)))


def to_list(data):
    if isinstance(data, list):
        return data
    else:
        return [data]


def find_setting_files():
    while True:
        selected_file = easygui.fileopenbox(msg="请选择 league_of_legends.live.product_settings.yaml 文件",
                                            default="C:/ProgramData",
                                            filetypes=["*.yaml"])
        if selected_file:
            print(f"您已选择: {selected_file}")
            return [selected_file]
        else:
            print("\n您未选择任何文件")
            decision = easygui.buttonbox(
                "您要重新选择文件，直接启动游戏，还是退出？\n",
                "您未选择任何文件",
                ["重新选择", "启动游戏", "退出"])
            if decision.lower() == '重新选择':
                continue
            elif decision.lower() == '启动游戏':
                print("直接启动游戏")
                return []
            elif decision.lower() == '退出':
                print("再见！")
                sys.exit()


def find_game_clients(default_dir="C:/"):
    while True:
        selected_file = easygui.fileopenbox(msg="请选择 RiotClientServices.exe 文件",
                                            default=default_dir,
                                            filetypes=["*.exe"])
        if selected_file:
            print(f"您已选择: {selected_file}")
            return [selected_file]
        else:
            print("\n您未选择任何程序")
            decision = easygui.buttonbox(
                "您要重新选择，还是退出？\n",
                "您未选择任何程序",
                ["重新选择", "退出"])
            if decision.lower() == '重新选择':
                continue
            elif decision.lower() == '退出':
                print("再见！")
                sys.exit()


def is_valid_settings(_settings):
    return _settings is not None and 'settings' in _settings and 'locale_data' in _settings


@contextmanager
def write_permission(file_path):
    try:
        os.chmod(file_path, stat.S_IWRITE)
        yield
    finally:
        os.chmod(file_path, stat.S_IREAD)


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def update_settings(_setting_files):
    yaml_settings = []
    _delayed_exit = False
    for setting_file in _setting_files:
        try:
            with write_permission(setting_file):
                print(f"更新设置文件: {setting_file}")
                yaml_content = read_yaml(setting_file)
                if not is_valid_settings(yaml_content):
                    print(f"无效文件: {setting_file}")
                    continue
                current_locale = yaml_content['settings']['locale']
                print(f"当前语言: {current_locale}")
                if current_locale != selected_locale:
                    print(f"正在备份文件...")
                    backup_file(setting_file)
                yaml_content['settings']['locale'] = selected_locale
                # when selected_locale is not in available_locales
                if selected_locale not in yaml_content['locale_data']["available_locales"]:
                    yaml_content['locale_data']["available_locales"].append(selected_locale)
                yaml_content['locale_data']["default_locale"] = selected_locale
                yaml_settings.append(yaml_content)
                write_yaml(setting_file, yaml_content)
                print(f"更新设置文件成功!")
        except Exception as e:
            print(f"更新设置文件失败: {setting_file}, error: {e}")
            _delayed_exit = True
    return yaml_settings, _delayed_exit


if __name__ == '__main__':

    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    selected_locale = "zh_CN"
    current_version = "1.0.1"
    delayed_exit = False
    # Get configuration file path
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".lolauncher")
    os.makedirs(config_dir, exist_ok=True)
    config_filename = os.path.join(config_dir, "config.json")

    # Read configuration file
    config = read_json(config_filename)
    selected_locale = config.get("Locale", selected_locale)

    # Check for updates
    repo_name = "ChenglongMa/LoLauncher"
    new_version, html_url = check_for_updates(repo_name, current_version)

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
            print("继续启动程序...")

    setting_files = filter_existing_files(to_list(config.get('SettingFile', [])))

    if not setting_files:
        print("开始尝试自动查找配置文件...")
        filename_suffix = r"ProgramData\Riot Games\Metadata\league_of_legends.live\league_of_legends.live.product_settings.yaml"
        for drive in get_drives():
            filename = os.path.join(drive, filename_suffix)
            if os.path.exists(filename):
                setting_files.append(filename)
        if len(setting_files) > 1:
            print("找到多个配置文件。")
        if not setting_files:
            print("未找到配置文件，请手动选择。")
            print(
                "该文件通常位于："
                r"[系统盘]:\ProgramData\Riot Games\Metadata\league_of_legends.live"
                r"\league_of_legends.live.product_settings.yaml"
            )
            setting_files = find_setting_files()
    settings, delayed_exit = update_settings(setting_files)

    product_install_root = settings[0]['product_install_root']

    product_install_root = product_install_root if os.path.exists(product_install_root) else "C:/"

    game_clients_in_settings = [
        os.path.join(setting['product_install_root'], "Riot Client/RiotClientServices.exe")
        for setting in settings
    ]
    game_clients = filter_existing_files(to_list(config.get('GameClient', [])) + game_clients_in_settings)
    if not game_clients:
        print("未找到 RiotClientServices.exe，请手动选择。")
        game_clients = find_game_clients(product_install_root)

    # Start game
    print("英雄联盟，启动！")
    game_client = os.path.normpath(game_clients[0])
    subprocess.run(['explorer.exe', game_client], check=False)

    config = {
        "@注意": r"请使用\或/做为路径分隔符，如 C:\ProgramData 或 C:/ProgramData",
        "@SettingFile": "请在下方填写 league_of_legends.live.product_settings.yaml 文件路径",
        "SettingFile": setting_files,
        "@GameClient": "请在下方填写 RiotClientServices.exe 文件路径",
        "GameClient": game_client,
        "Locale": selected_locale,
    }
    write_json(config_filename, config)

    if delayed_exit:
        input("按回车键退出...")
        sys.exit()
    else:
        delay_seconds = 5

        for i in range(delay_seconds):
            print(f"{delay_seconds - i} 秒后退出...", end='\r')
            time.sleep(1)
        sys.exit()
