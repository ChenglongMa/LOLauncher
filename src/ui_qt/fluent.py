from PySide6.QtWidgets import QComboBox, QFrame, QPushButton

try:
    from qfluentwidgets import (
        CardWidget,
        ComboBox,
        FluentIcon,
        PrimaryPushButton,
        PushButton,
        SwitchButton,
        Theme,
        setTheme,
    )
except Exception:
    CardWidget = QFrame
    ComboBox = QComboBox
    PrimaryPushButton = QPushButton
    PushButton = QPushButton
    SwitchButton = None
    FluentIcon = None
    Theme = None

    def setTheme(theme):
        return None


def apply_theme(theme: str) -> None:
    if Theme is None:
        return
    setTheme(Theme.DARK if "dark" in theme.lower() else Theme.LIGHT)

