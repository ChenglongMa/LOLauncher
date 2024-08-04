import ctypes

ctypes.windll.shcore.SetProcessDpiAwareness(0)
ctypes.windll.user32.SetProcessDPIAware()
