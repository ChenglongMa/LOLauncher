import re
import sys
from dataclasses import dataclass
from typing import Callable

from github import Github, GithubException

from core.constants import REPO_NAME, VERSION
from core.dialogs import DialogService
from core.platform import open_web


@dataclass(frozen=True)
class ReleaseUpdate:
    tag: str
    url: str
    notes: str


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"[vV]?([0-9]+\.[0-9]+\.[0-9]+)", value.strip())
    return tuple(map(int, match[1].split("."))) if match else ()


def is_newer_version(candidate: str, current: str) -> bool:
    current_version = version_tuple(current)
    return bool(current_version) and version_tuple(candidate) > current_version


def get_updates(repo_name: str = REPO_NAME, current_version: str = VERSION) -> ReleaseUpdate | None:
    with Github(retry=None, timeout=5) as github:
        release = github.get_repo(repo_name, lazy=True).get_latest_release()
        if release.draft or release.prerelease or not is_newer_version(release.tag_name, current_version):
            return None
        return ReleaseUpdate(release.tag_name, release.html_url, (release.body or "").strip())


def check_for_updates(
    dialog: DialogService | None = None,
    on_status: Callable[[str], None] = print,
) -> bool:
    try:
        update = get_updates()
    except (GithubException, OSError) as error:
        print(f"检查更新失败: {error}")
        on_status("暂时无法检查更新，请稍后重试。")
        return False
    if update is None:
        on_status("当前已是最新版本")
        return False

    print(f"发现新版本 {update.tag}\n{update.url}")
    if dialog is None or dialog.choose(
        "发现新版本",
        f"新版本 {update.tag} 已发布。可在发布页查看更新说明并下载。",
        ["前往下载", "继续使用该版本"],
        details=update.notes,
    ) == "前往下载":
        open_web(update.url)
        sys.exit(0)
    return True

