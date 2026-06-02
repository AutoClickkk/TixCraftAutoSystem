from __future__ import annotations
import os
from pathlib import Path

import pytest

from src.utils import driver_factory


def test_platform_dir_returns_known_value():
    p = driver_factory._platform_dir()
    assert p in ("mac-arm64", "mac-x64", "win64", "linux64")


def test_pid_alive_for_self():
    assert driver_factory._pid_alive(os.getpid()) is True


def test_pid_alive_for_obviously_dead():
    # PID 0 is special (init/scheduler on some OS); use a huge unlikely PID.
    assert driver_factory._pid_alive(9_999_999) is False


def test_clean_stale_chrome_locks_removes_dead_pid_symlink(tmp_path: Path):
    profile = tmp_path / "profile"
    profile.mkdir()
    # Simulate a stale SingletonLock pointing at a dead PID.
    (profile / "SingletonLock").symlink_to("Mac.localdomain-9999999")
    driver_factory._clean_stale_chrome_locks(profile)
    assert not (profile / "SingletonLock").exists() and not (profile / "SingletonLock").is_symlink()


def test_clean_stale_chrome_locks_preserves_live_pid(tmp_path: Path):
    profile = tmp_path / "profile"
    profile.mkdir()
    # Symlink with own PID = live, should NOT be removed
    (profile / "SingletonLock").symlink_to(f"Mac.localdomain-{os.getpid()}")
    driver_factory._clean_stale_chrome_locks(profile)
    assert (profile / "SingletonLock").is_symlink()


def test_clean_stale_chrome_locks_noop_when_missing(tmp_path: Path):
    profile = tmp_path / "profile"
    profile.mkdir()
    # No SingletonLock file at all — should silently succeed.
    driver_factory._clean_stale_chrome_locks(profile)
