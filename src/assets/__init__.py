import os
import sys


def get_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    else:
        return filename


def get_icon(icon_name):
    if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS'):
        # The application is frozen (i.e., it's been packaged into an executable)
        application_path = os.path.join(sys._MEIPASS, "assets")
    else:
        # The application is not frozen
        # (i.e., it's running in a normal Python environment)
        application_path = os.path.dirname(__file__)

    return os.path.join(application_path, icon_name)
