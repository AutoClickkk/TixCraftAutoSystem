from __future__ import annotations
import json
from pathlib import Path

import pytest

from src.services.datacenter import DataCenter, DEFAULT_CONFIG


@pytest.fixture
def tmp_config(tmp_path: Path):
    cfg = {
        "game_id": "test_show",
        "number_of_ticket": 3,
        "show_time_text_contains": "2026/06/06",
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    dc = DataCenter()
    dc.set_path(p)
    return dc, p, cfg


def test_get_config_merges_with_defaults(tmp_config):
    dc, _path, written = tmp_config
    loaded = dc.get_config(reload=True)
    # User values preserved
    assert loaded["game_id"] == written["game_id"]
    assert loaded["number_of_ticket"] == 3
    # Defaults filled in for absent keys
    for key in DEFAULT_CONFIG:
        assert key in loaded


def test_save_round_trip(tmp_path: Path):
    dc = DataCenter()
    dc.set_path(tmp_path / "out.json")
    cfg = {**DEFAULT_CONFIG, "game_id": "abc", "number_of_ticket": 4}
    dc.save(cfg)

    # Re-read raw file
    raw = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert raw["game_id"] == "abc"
    assert raw["number_of_ticket"] == 4


def test_get_config_when_file_missing_returns_defaults(tmp_path: Path):
    dc = DataCenter()
    dc.set_path(tmp_path / "does_not_exist.json")
    cfg = dc.get_config(reload=True)
    assert cfg == DEFAULT_CONFIG
