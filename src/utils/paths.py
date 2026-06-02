from __future__ import annotations
from pathlib import Path
import os
import shutil
import sys


APP_NAME = "TixCraftAutoSystem"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def bundle_dir() -> Path:
    """Directory where bundled resources live (project root in dev, MEIPASS in frozen)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def resource_search_paths() -> list[Path]:
    """Where to look for bundled data files. On macOS .app bundles, post-build
    copies live in Contents/Resources but `_MEIPASS` points at Contents/Frameworks,
    so we have to check both."""
    out = [bundle_dir()]
    if is_frozen() and sys.platform == "darwin":
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        if meipass:
            resources = meipass.parent / "Resources"
            if resources.exists() and resources not in out:
                out.append(resources)
    return out


def find_resource(*parts: str) -> Path:
    """Resolve a bundled resource path across MEIPASS and (on macOS) Resources/.
    Returns the first path that exists; if none exist, returns the bundle_dir() path."""
    for root in resource_search_paths():
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate
    return bundle_dir().joinpath(*parts)


def user_data_dir() -> Path:
    """Per-user writable directory. ~/Library/Application Support on macOS, %APPDATA% on Windows."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    """Writable config.json path. In frozen mode this is in user_data_dir;
    in dev mode this is the project root so editing one file matches the README."""
    if is_frozen():
        path = user_data_dir() / "config.json"
        if not path.exists():
            seed = bundle_dir() / "config_sample.json"
            if seed.exists():
                shutil.copy(seed, path)
        return path
    return bundle_dir() / "config.json"


def env_path() -> Path:
    """Path to .env. In frozen mode lives in user_data_dir."""
    if is_frozen():
        return user_data_dir() / ".env"
    return bundle_dir() / ".env"


def version_file_path() -> Path:
    return bundle_dir() / "version.json"


def log_dir() -> Path:
    path = user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
