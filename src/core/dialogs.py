from typing import Protocol, Sequence


class DialogService(Protocol):
    def confirm(self, title: str, message: str) -> bool:
        ...

    def choose(self, title: str, message: str, choices: Sequence[str], *, details: str = "") -> str | None:
        ...

    def input_text(self, title: str, message: str, default: str = "") -> str | None:
        ...

    def select_file(
        self,
        title: str,
        file_types: Sequence[tuple[str, str]],
        initial_dir: str = "",
        initial_file: str = "",
    ) -> str | None:
        ...

    def info(self, title: str, message: str) -> None:
        ...

    def error(self, title: str, message: str) -> None:
        ...

