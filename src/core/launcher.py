import os

from watchdog.events import FileSystemEventHandler

from core.config import filter_existing_files, normalize_file_path, read_json, to_list, update_settings
from core.constants import RIOT_DATA_DIR
from core.dialogs import DialogService
from core.platform import launch_explorer


class FileWatcher(FileSystemEventHandler):
    def __init__(self, *watching_files: str, selected_locale: str, msg_callback_fn=None):
        self.watching_files = {os.path.normcase(normalize_file_path(path)) for path in watching_files}
        print(f"Watching files: {self.watching_files}")
        self.selected_locale = selected_locale
        self.msg_callback_fn = msg_callback_fn or print
        super().__init__()

    def on_modified(self, event):
        if not event.is_directory:
            self.apply_locale(event.src_path)

    on_created = on_modified

    def on_moved(self, event):
        if not event.is_directory:
            self.apply_locale(event.dest_path)

    def apply_locale(self, file_path):
        if file_path and os.path.normcase(normalize_file_path(file_path)) in self.watching_files:
            update_settings(file_path, self.selected_locale, self.msg_callback_fn)


def game_clients_from_settings(settings: tuple[dict, ...]) -> list[str]:
    clients = []
    for setting in settings:
        install_root = setting.get("product_install_root") if setting else None
        if isinstance(install_root, str) and install_root:
            clients.append(os.path.join(install_root, "Riot Client", "RiotClientServices.exe"))
    return clients


def choose_game_client(configured_clients, settings: tuple[dict, ...], dialog: DialogService) -> str | None:
    game_clients = filter_existing_files(to_list(configured_clients) + game_clients_from_settings(settings))
    if not game_clients:
        installs = read_json(os.path.join(RIOT_DATA_DIR, "RiotClientInstalls.json"))
        registered_clients = filter_existing_files([installs.get("rc_live"), installs.get("rc_default")])
        return next(iter(registered_clients), None)
    if len(game_clients) == 1:
        return game_clients[0]
    return dialog.choose("找到多个游戏路径，请选择一个", "请从以下选项中选择一个游戏启动路径", game_clients)


def start_game(configured_clients, settings: tuple[dict, ...], dialog: DialogService) -> str | None:
    selected_client = choose_game_client(configured_clients, settings, dialog)
    if selected_client:
        launch_explorer(selected_client)
    return selected_client

