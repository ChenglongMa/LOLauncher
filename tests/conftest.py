import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def riot_metadata(tmp_path, monkeypatch):
    metadata = tmp_path / "Metadata"
    monkeypatch.setattr("core.config.DEFAULT_METADATA_DIR", str(metadata))
    monkeypatch.setattr("core.config.get_drives", lambda: [])

    def write_settings(installation):
        path = metadata / installation / f"{installation}.product_settings.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('settings:\n    locale: "en_US"  # Riot language\n    other_setting: true\n', encoding="utf-8")
        return path

    return write_settings


class FakeDialog:
    def __init__(self, choices=None, text=None, file_path=None):
        self.choices = list(choices or [])
        self.text = text
        self.file_path = file_path
        self.messages = []

    def confirm(self, title, message):
        self.messages.append((title, message))
        return bool(self.choices.pop(0)) if self.choices else True

    def choose(self, title, message, choices):
        self.messages.append((title, message, tuple(choices)))
        return self.choices.pop(0) if self.choices else choices[0]

    def input_text(self, title, message, default=""):
        self.messages.append((title, message, default))
        return self.text if self.text is not None else default

    def select_file(self, title, file_types, initial_dir="", initial_file=""):
        self.messages.append((title, tuple(file_types), initial_dir, initial_file))
        return self.file_path

    def info(self, title, message):
        self.messages.append((title, message))

    def error(self, title, message):
        self.messages.append((title, message))

