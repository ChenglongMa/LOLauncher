import os

from watchdog.events import FileSystemEventHandler

from core.config import filter_existing_files, normalize_file_path, read_yaml, update_settings
from core.dialogs import DialogService
from core.platform import launch_explorer


class FileWatcher(FileSystemEventHandler):
    def __init__(self, *watching_files: str, selected_locale: str, msg_callback_fn=None):
        self.watching_files = filter_existing_files(watching_files)
        print(f"Watching files: {self.watching_files}")
        self.selected_locale = selected_locale
        self.msg_callback_fn = msg_callback_fn or print
        super().__init__()

    def on_modified(self, event):
        print(f"event type: {event.event_type}  path : {event.src_path}")
        if normalize_file_path(event.src_path) in self.watching_files:
            print(f"File {event.src_path} has been modified")
            content = read_yaml(event.src_path)
            if not content or "settings" not in content:
                print(f"Invalid file: {event.src_path}")
                return
            curr_locale = content["settings"]["locale"]
            if curr_locale != self.selected_locale:
                self.msg_callback_fn(f"正在将语言 {curr_locale} 更新为 {self.selected_locale} ...")
                update_settings(event.src_path, self.selected_locale, self.msg_callback_fn)


def game_clients_from_settings(settings: tuple[dict, ...]) -> list[str]:
    return [
        os.path.join(setting["product_install_root"], "Riot Client/RiotClientServices.exe")
        for setting in settings
        if setting and setting.get("product_install_root")
    ]


def choose_game_client(configured_clients, settings: tuple[dict, ...], dialog: DialogService) -> str | None:
    configured = configured_clients if isinstance(configured_clients, list) else [configured_clients]
    game_clients = filter_existing_files(configured + game_clients_from_settings(settings))
    if not game_clients:
        return None
    if len(game_clients) == 1:
        return game_clients[0]
    return dialog.choose("找到多个游戏路径，请选择一个", "请从以下选项中选择一个游戏启动路径", game_clients)


def start_game(configured_clients, settings: tuple[dict, ...], dialog: DialogService) -> str | None:
    selected_client = choose_game_client(configured_clients, settings, dialog)
    if selected_client:
        launch_explorer(selected_client)
    return selected_client

