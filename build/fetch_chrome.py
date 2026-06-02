"""Download Chrome for Testing + matching chromedriver for the host platform
and stage them under assets/chrome/. Run from project root before PyInstaller.

Usage:  python build/fetch_chrome.py [--channel Stable]
"""
from __future__ import annotations
import argparse
import io
import json
import os
import platform
import shutil
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path


CFT_INDEX = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"


def detect_platform() -> str:
    sysname = platform.system().lower()
    mach = platform.machine().lower()
    if sysname == "darwin":
        return "mac-arm64" if mach in ("arm64", "aarch64") else "mac-x64"
    if sysname == "windows":
        return "win64"
    return "linux64"


def download(url: str) -> bytes:
    print(f"  ↓ {url}")
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read()


def extract_zip(blob: bytes, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(dest)
    # Restore +x on POSIX since zipfile drops perms
    if os.name != "nt":
        for root, _, files in os.walk(dest):
            for f in files:
                p = Path(root) / f
                if f in ("chrome", "chromedriver") or p.suffix in (".app", ""):
                    try:
                        p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                    except Exception:
                        pass
    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", default="Stable",
                        choices=["Stable", "Beta", "Dev", "Canary"])
    parser.add_argument("--platform", default=None,
                        help="Override platform (mac-arm64 / mac-x64 / win64)")
    args = parser.parse_args()

    plat = args.platform or detect_platform()
    print(f"[fetch_chrome] platform = {plat}, channel = {args.channel}")

    print("[fetch_chrome] fetching version index…")
    index = json.loads(download(CFT_INDEX))
    channel = index["channels"][args.channel]
    version = channel["version"]
    print(f"[fetch_chrome] version = {version}")

    def find_url(bucket: str) -> str:
        for entry in channel["downloads"][bucket]:
            if entry["platform"] == plat:
                return entry["url"]
        raise RuntimeError(f"no {bucket} download for {plat}")

    chrome_url = find_url("chrome")
    driver_url = find_url("chromedriver")

    root = Path(__file__).resolve().parent.parent / "assets" / "chrome" / plat
    if root.exists():
        print(f"[fetch_chrome] cleaning {root}")
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    print("[fetch_chrome] downloading chrome…")
    extract_zip(download(chrome_url), root)
    print("[fetch_chrome] downloading chromedriver…")
    extract_zip(download(driver_url), root)

    (root / "VERSION").write_text(f"{version}\n", encoding="utf-8")
    print(f"[fetch_chrome] done → {root}")
    print(f"  size: {sum(f.stat().st_size for f in root.rglob('*') if f.is_file()) / 1024 / 1024:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
