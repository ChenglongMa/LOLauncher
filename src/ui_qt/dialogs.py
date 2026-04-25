from collections.abc import Sequence

from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMessageBox, QWidget


def ensure_qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class QtDialogService:
    def __init__(self, parent: QWidget | None = None):
        ensure_qapplication()
        self.parent = parent

    def set_parent(self, parent: QWidget | None) -> None:
        self.parent = parent

    def confirm(self, title: str, message: str) -> bool:
        result = QMessageBox.question(self.parent, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        return result == QMessageBox.Yes

    def choose(self, title: str, message: str, choices: Sequence[str]) -> str | None:
        if not choices:
            return None
        box = QMessageBox(self.parent)
        box.setWindowTitle(title)
        box.setText(message)
        buttons = {}
        for choice in choices:
            buttons[box.addButton(choice, QMessageBox.AcceptRole)] = choice
        box.exec()
        return buttons.get(box.clickedButton())

    def input_text(self, title: str, message: str, default: str = "") -> str | None:
        text, ok = QInputDialog.getText(self.parent, title, message, text=default)
        return text if ok else None

    def select_file(
        self,
        title: str,
        file_types: Sequence[tuple[str, str]],
        initial_dir: str = "",
        initial_file: str = "",
    ) -> str | None:
        filters = ";;".join(f"{name} ({pattern})" for name, pattern in file_types)
        start_path = initial_dir
        if initial_file:
            start_path = f"{initial_dir}/{initial_file}" if initial_dir else initial_file
        selected_file, _ = QFileDialog.getOpenFileName(self.parent, title, start_path, filters)
        return selected_file or None

    def info(self, title: str, message: str) -> None:
        QMessageBox.information(self.parent, title, message)

    def error(self, title: str, message: str) -> None:
        QMessageBox.critical(self.parent, title, message)

