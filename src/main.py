import sys
import threading
from ui.app import App
from utils import read_json, check_for_updates, verify_metadata_file, singleton, show_existing_instance, start_server, \
    CONFIG_FILENAME, GUI_CONFIG_FILENAME

if __name__ == '__main__':
    # if not is_admin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()
    # Don't need to run as administrator since v1.0.2

    main_instance = singleton()
    if not main_instance:
        show_existing_instance()
        sys.exit(0)
    check_for_updates()


    def on_message(message):
        if message == "SHOW_YOURSELF":
            app.show_window()


    server_thread = threading.Thread(target=start_server, args=(on_message,), daemon=True)
    server_thread.start()

    config = read_json(CONFIG_FILENAME) or {}
    ui_config = read_json(GUI_CONFIG_FILENAME) or {}
    setting_files = verify_metadata_file(config)

    app = App(setting_files, config, ui_config)
    app.run()
