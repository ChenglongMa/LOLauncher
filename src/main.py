import os
import sys

from ui import App
from utils import read_json, check_for_updates, verify_metadata_file, read_yaml

if __name__ == '__main__':

    # if not is_admin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()
    # Don't need to run as administrator since v1.0.2

    check_for_updates()

    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".lolauncher")
    os.makedirs(config_dir, exist_ok=True)
    config_filename = os.path.join(config_dir, "config.json")

    config = read_json(config_filename)

    setting_file = verify_metadata_file(config)

    app = App(setting_file, config, config_filename)
    app.run()
