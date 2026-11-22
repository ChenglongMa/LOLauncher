import ctypes
import sys
import tkinter as tk

from core.config import ensure_config_dir, read_json, verify_metadata_file
from core.constants import CONFIG_FILENAME, GUI_CONFIG_FILENAME
from core.platform import show_existing_instance, singleton, start_server
from core.updates import check_for_updates
from ui.app import App
from ui.dialogs import TkDialogService


def main() -> int:
    if not singleton():
        show_existing_instance()
        return 0

    ensure_config_dir()
    ctypes.windll.user32.SetProcessDPIAware()
    root = tk.Tk()
    root.withdraw()
    try:
        dialog = TkDialogService(root)
        check_for_updates(dialog, print)

        config = read_json(CONFIG_FILENAME)
        ui_config = read_json(GUI_CONFIG_FILENAME)
        setting_files = verify_metadata_file(config, dialog)
        app = App(setting_files, config, ui_config, root=root, dialog=dialog)

        def on_message(message):
            if message == "SHOW_YOURSELF":
                app.request_show()

        start_server(on_message)
        return app.run()
    finally:
        root.destroy()


if __name__ == "__main__":
    sys.exit(main())
