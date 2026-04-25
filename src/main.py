import sys

from core.config import ensure_config_dir, read_json, verify_metadata_file
from core.constants import CONFIG_FILENAME, GUI_CONFIG_FILENAME
from core.platform import show_existing_instance, singleton, start_server
from core.updates import check_for_updates
from ui_qt.app import App
from ui_qt.dialogs import QtDialogService, ensure_qapplication

if __name__ == '__main__':
    # if not is_admin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()
    # Don't need to run as administrator since v1.0.2

    main_instance = singleton()
    if not main_instance:
        show_existing_instance()
        sys.exit(0)

    ensure_config_dir()
    ensure_qapplication()
    dialog = QtDialogService()
    check_for_updates(dialog, print)

    config = read_json(CONFIG_FILENAME) or {}
    ui_config = read_json(GUI_CONFIG_FILENAME) or {}
    setting_files = verify_metadata_file(config, dialog)

    def on_message(message):
        if message == 'SHOW_YOURSELF':
            app.request_show()


    app = App(setting_files, config, ui_config, dialog=dialog)
    start_server(on_message)

    sys.exit(app.run())
