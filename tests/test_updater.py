from __future__ import annotations
from unittest.mock import patch, MagicMock

import pytest

from src.services import updater
from src.services.updater import Asset, UpdateInfo


@pytest.mark.parametrize("tag,want", [
    ("v0.2.1", "0.2.1"),
    ("0.2.1", "0.2.1"),
    ("V1.0", "V1.0"),  # only leading "v" lowercase is stripped per implementation
])
def test_normalize_tag(tag, want):
    assert updater._normalize_tag(tag) == want


@pytest.mark.parametrize("latest,current,expected", [
    ("0.2.1", "0.2.0", True),
    ("v0.2.1", "v0.2.0", True),
    ("0.2.0", "0.2.0", False),
    ("0.2.0", "0.2.1", False),
    ("1.0.0", "0.9.9", True),
])
def test_is_newer(latest, current, expected):
    assert updater._is_newer(latest, current) is expected


def test_pick_platform_asset_mac_prefers_dmg(monkeypatch):
    monkeypatch.setattr("sys.platform", "darwin")
    assets = [
        Asset(name="release-notes.txt", download_url="x", size=1),
        Asset(name="準點搶-mac-arm64.zip", download_url="z", size=2),
        Asset(name="準點搶.dmg", download_url="d", size=3),
    ]
    picked = updater.pick_platform_asset(assets)
    assert picked is not None
    assert picked.name.endswith(".dmg")


def test_pick_platform_asset_windows_prefers_exe(monkeypatch):
    monkeypatch.setattr("sys.platform", "win32")
    assets = [
        Asset(name="release-notes.txt", download_url="x", size=1),
        Asset(name="準點搶-win-x64.zip", download_url="z", size=2),
    ]
    picked = updater.pick_platform_asset(assets)
    assert picked is not None
    assert "win" in picked.name.lower()


def test_pick_platform_asset_empty_returns_none():
    assert updater.pick_platform_asset([]) is None


def test_check_for_update_handles_404():
    with patch("src.services.updater.requests.get") as mock_get:
        resp = MagicMock(status_code=404)
        mock_get.return_value = resp
        info = updater.check_for_update(repo="not/exist")
    assert info.has_update is False
    assert info.error is not None


def test_check_for_update_network_error():
    import requests
    with patch("src.services.updater.requests.get") as mock_get:
        mock_get.side_effect = requests.ConnectionError("offline")
        info = updater.check_for_update(repo="x/y")
    assert info.has_update is False
    assert "網路" in info.error or "error" in info.error.lower()


def test_check_for_update_detects_newer():
    with patch("src.services.updater.requests.get") as mock_get:
        resp = MagicMock(status_code=200)
        resp.json.return_value = {
            "tag_name": "v9.9.9",
            "body": "release notes",
            "html_url": "https://example.com/release",
            "assets": [
                {"name": "準點搶-mac-arm64.zip", "browser_download_url": "https://x", "size": 100},
            ],
        }
        mock_get.return_value = resp
        info = updater.check_for_update(repo="x/y")
    assert info.has_update is True
    assert info.latest_version == "9.9.9"
    assert len(info.assets) == 1
