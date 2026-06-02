from __future__ import annotations
from pathlib import Path

from src.utils import paths


def test_bundle_dir_in_dev_points_at_project_root():
    bd = paths.bundle_dir()
    assert bd.name == "TixCraftAutoSystem" or (bd / "src").is_dir()


def test_user_data_dir_is_creatable(tmp_path, monkeypatch):
    # Redirect HOME so we don't actually pollute the user dir.
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    udir = paths.user_data_dir()
    assert udir.exists()
    assert paths.APP_NAME in str(udir)


def test_find_resource_returns_existing_path():
    # version.json is always shipped at bundle root
    p = paths.find_resource("version.json")
    assert p.exists()
