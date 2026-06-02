from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import re

import requests
from packaging.version import Version, InvalidVersion

from ..utils import paths


GITHUB_API = "https://api.github.com"
TIMEOUT_SECONDS = 8
# Fallback repo so the updater works even if version.json doesn't expose it.
DEFAULT_REPO = "AutoClickkk/TixCraftAutoSystem"


@dataclass(frozen=True)
class Asset:
    name: str
    download_url: str
    size: int


@dataclass(frozen=True)
class UpdateInfo:
    current_version: str
    latest_version: Optional[str]
    has_update: bool
    release_url: str
    body: str
    assets: List[Asset]
    error: Optional[str] = None


def _read_version_meta() -> Dict[str, Any]:
    path: Path = paths.version_file_path()
    if not path.exists():
        return {"version": "0.0.0", "github_repo": ""}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": "0.0.0", "github_repo": ""}


def get_current_version() -> str:
    return str(_read_version_meta().get("version", "0.0.0"))


def get_github_repo() -> str:
    return str(_read_version_meta().get("github_repo") or DEFAULT_REPO)


def _normalize_tag(tag: str) -> str:
    return re.sub(r"^v", "", tag).strip()


def _is_newer(latest: str, current: str) -> bool:
    try:
        return Version(_normalize_tag(latest)) > Version(_normalize_tag(current))
    except InvalidVersion:
        return latest != current


def check_for_update(repo: Optional[str] = None) -> UpdateInfo:
    """Query GitHub Releases for the latest release of `repo` (owner/name).
    Falls back to the repo from version.json if not provided."""
    current = get_current_version()
    repo = (repo or get_github_repo()).strip()
    if not repo or repo.startswith("YOUR_"):
        return UpdateInfo(
            current_version=current,
            latest_version=None,
            has_update=False,
            release_url="",
            body="",
            assets=[],
            error="尚未設定更新檢查 endpoint",
        )

    url = f"{GITHUB_API}/repos/{repo}/releases/latest"
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
            headers={"Accept": "application/vnd.github+json"},
        )
        if resp.status_code == 404:
            return UpdateInfo(
                current_version=current,
                latest_version=None,
                has_update=False,
                release_url=f"https://github.com/{repo}/releases",
                body="",
                assets=[],
                error="repo 尚未發佈 release",
            )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return UpdateInfo(
            current_version=current,
            latest_version=None,
            has_update=False,
            release_url="",
            body="",
            assets=[],
            error=f"網路錯誤: {e}",
        )

    tag = str(data.get("tag_name") or "")
    latest = _normalize_tag(tag) or None
    assets = [
        Asset(
            name=a.get("name", ""),
            download_url=a.get("browser_download_url", ""),
            size=int(a.get("size") or 0),
        )
        for a in (data.get("assets") or [])
    ]
    body = str(data.get("body") or "")
    release_url = str(data.get("html_url") or f"https://github.com/{repo}/releases")

    has_update = bool(latest) and _is_newer(latest, current)

    return UpdateInfo(
        current_version=current,
        latest_version=latest,
        has_update=has_update,
        release_url=release_url,
        body=body,
        assets=assets,
    )


def pick_platform_asset(assets: List[Asset]) -> Optional[Asset]:
    """Pick the asset for the current platform."""
    import sys
    if not assets:
        return None
    if sys.platform == "darwin":
        keywords = ("mac",)
        priority_ext = (".dmg",)
    elif sys.platform.startswith("win"):
        keywords = ("win",)
        priority_ext = (".exe",)
    else:
        keywords = ("linux",)
        priority_ext = (".tar.gz",)

    # 1. Prefer dmg/exe/tar.gz outright
    for ext in priority_ext:
        for a in assets:
            if a.name.lower().endswith(ext):
                return a
    # 2. A zip whose name contains the platform keyword
    for a in assets:
        name = a.name.lower()
        if name.endswith(".zip") and any(k in name for k in keywords):
            return a
    # 3. Fall back to anything
    return assets[0]
