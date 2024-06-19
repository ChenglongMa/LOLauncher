import os

from ui.app import App
from utils import read_json, check_for_updates, verify_metadata_file, CONFIG_FILENAME, GUI_CONFIG_FILENAME

if __name__ == '__main__':
    # if not is_admin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()
    # Don't need to run as administrator since v1.0.2

    check_for_updates()

    config = read_json(CONFIG_FILENAME) or {}
    ui_config = read_json(GUI_CONFIG_FILENAME) or {}
    setting_file = verify_metadata_file(config)

    app = App(setting_file, config, ui_config)
    app.run()
