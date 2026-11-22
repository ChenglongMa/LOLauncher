import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

from conftest import FakeDialog
from core.constants import REPO_NAME, VERSION
from core.updates import ReleaseUpdate, check_for_updates, get_updates


@pytest.fixture
def latest_release(mocker):
    release = SimpleNamespace(
        tag_name="1.3.0",
        html_url=f"https://github.com/{REPO_NAME}/releases/tag/1.3.0",
        body="支持独立版云顶之弈的语言设置。",
        draft=False,
        prerelease=False,
    )
    github = mocker.patch("core.updates.Github").return_value.__enter__.return_value
    github.get_repo.return_value.get_latest_release.return_value = release
    return release


@pytest.fixture
def newer_release(latest_release):
    major, minor, patch = map(int, VERSION.split("."))
    latest_release.tag_name = f"{major}.{minor}.{patch + 1}"
    latest_release.html_url = f"https://github.com/{REPO_NAME}/releases/tag/{latest_release.tag_name}"
    return latest_release


def test_version_matches_project_lockfile_and_windows_metadata():
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    locked_project = next(package for package in lock["package"] if package["name"] == project["name"])
    windows_metadata = YAML(typ="safe").load((root / "metadata.yml").read_text(encoding="utf-8"))

    assert VERSION == project["version"] == locked_project["version"] == windows_metadata["Version"]


def test_stable_release_is_newer_than_122_but_matches_installed_130(latest_release):
    assert get_updates(current_version="1.2.2") == ReleaseUpdate(
        latest_release.tag_name, latest_release.html_url, latest_release.body,
    )
    assert get_updates(current_version="1.3.0") is None


@pytest.mark.parametrize("flag", ["draft", "prerelease"])
def test_updates_ignore_unpublished_or_preview_releases(latest_release, flag):
    setattr(latest_release, flag, True)
    assert get_updates(current_version="1.2.2") is None


def test_update_notification_displays_release_notes(newer_release):
    dialog = FakeDialog(choices=["继续使用该版本"])

    assert check_for_updates(dialog) is True
    title, message, choices, notes = dialog.messages[-1]
    assert title == "发现新版本"
    assert newer_release.tag_name in message
    assert "前往下载" in choices
    assert notes == newer_release.body


def test_update_opens_release_page_when_user_chooses_download(newer_release, mocker):
    dialog = FakeDialog(choices=["前往下载"])
    open_web = mocker.patch("core.updates.open_web")

    with pytest.raises(SystemExit) as exit_result:
        check_for_updates(dialog)

    assert exit_result.value.code == 0
    open_web.assert_called_once_with(newer_release.html_url)


def test_failed_update_check_has_its_own_status(mocker):
    mocker.patch("core.updates.get_updates", side_effect=OSError("network unavailable"))
    status = mocker.Mock()

    assert check_for_updates(FakeDialog(), status) is False
    status.assert_called_once_with("暂时无法检查更新，请稍后重试。")
