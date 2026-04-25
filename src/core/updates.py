import re
import sys

from github import Github

from core.constants import REPO_NAME, VERSION
from core.dialogs import DialogService
from core.platform import open_web


def version_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", value))


def is_newer_version(candidate: str, current: str) -> bool:
    return version_tuple(candidate) > version_tuple(current)


def get_updates(repo_name: str = REPO_NAME, current_version: str = VERSION) -> tuple[str | None, str | None]:
    try:
        repo = Github(retry=None).get_repo(repo_name)
        latest_release = repo.get_latest_release()
        if is_newer_version(latest_release.tag_name, current_version):
            return latest_release.tag_name, latest_release.html_url
    except Exception:
        pass
    return None, None


def check_for_updates(dialog: DialogService | None = None, no_new_version_callback=None) -> bool:
    new_version, html_url = get_updates(REPO_NAME, VERSION)
    if new_version and html_url:
        print(f"发现新版本: {new_version}\n{html_url}")
        if dialog is None:
            open_web(html_url)
            sys.exit()
        decision = dialog.choose(
            "发现新版本",
            f"发现新版本: {new_version}\n您要更新吗？",
            ["前往下载", "继续使用该版本"],
        )
        if decision == "前往下载":
            open_web(html_url)
            sys.exit()
        return True

    callback = no_new_version_callback or print
    callback("当前已是最新版本")
    return False

