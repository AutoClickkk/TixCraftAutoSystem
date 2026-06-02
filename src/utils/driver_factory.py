from __future__ import annotations
from typing import Optional
from pathlib import Path
import os
import platform
import shutil
import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver

from . import logutils, paths


_log = logutils.LogUtils()

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)


def _platform_dir() -> str:
    sysname = sys.platform
    mach = platform.machine().lower()
    if sysname == "darwin":
        return "mac-arm64" if mach in ("arm64", "aarch64") else "mac-x64"
    if sysname.startswith("win"):
        return "win64"
    return "linux64"


def _bundled_root() -> Path:
    return paths.find_resource("assets", "chrome", _platform_dir())


def _bundled_chrome_binary() -> Optional[Path]:
    root = _bundled_root()
    candidates = [
        # macOS
        root / "chrome-mac-arm64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing",
        root / "chrome-mac-x64" / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing",
        # Windows
        root / "chrome-win64" / "chrome.exe",
        # Linux
        root / "chrome-linux64" / "chrome",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _bundled_chromedriver() -> Optional[Path]:
    root = _bundled_root()
    candidates = [
        root / "chromedriver-mac-arm64" / "chromedriver",
        root / "chromedriver-mac-x64" / "chromedriver",
        root / "chromedriver-win64" / "chromedriver.exe",
        root / "chromedriver-linux64" / "chromedriver",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _system_chromedriver() -> Optional[str]:
    on_path = shutil.which("chromedriver")
    if on_path:
        return on_path
    for c in (
        Path.home() / ".cache" / "selenium" / "chromedriver",
        Path("/usr/local/bin/chromedriver"),
        Path("/opt/homebrew/bin/chromedriver"),
    ):
        if c.exists():
            return str(c)
    return None


def _profile_dir() -> Path:
    """Persistent Chrome profile so the user only logs in once."""
    p = paths.user_data_dir() / "chrome-profile"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


def _clean_stale_chrome_locks(profile_dir: Path) -> None:
    """Chrome stores SingletonLock/Cookie/Socket symlinks to detect a running
    instance on the same profile. If a previous run crashed or was force-killed
    those files stay behind and Chrome refuses to start ("Chrome instance
    exited"). Remove them when the owning PID is gone."""
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        p = profile_dir / name
        try:
            if not p.exists() and not p.is_symlink():
                continue
            stale = True
            if p.is_symlink():
                try:
                    target = os.readlink(p)
                    pid = int(target.rsplit("-", 1)[-1])
                    if _pid_alive(pid):
                        stale = False
                except (ValueError, OSError):
                    pass
            if stale:
                try:
                    p.unlink()
                except IsADirectoryError:
                    shutil.rmtree(p, ignore_errors=True)
                except Exception:
                    pass
                _log.info(f"清除殘留的 Chrome lock: {name}")
        except Exception:
            pass


def create_chrome_driver(
    headless: bool = False,
    window_size: tuple[int, int] = (1280, 800),
    user_data_dir: Optional[str] = None,
) -> WebDriver:
    """Launch Chrome. Prefers the bundled Chrome for Testing so the user never
    needs to install Chrome or a matching chromedriver.

    Lookup order:
      1. Bundled Chrome + bundled chromedriver under assets/chrome/<platform>/
      2. Selenium Manager (built into selenium 4.6+) — falls back to system Chrome.
    """
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    options.add_argument(f"--user-agent={_DEFAULT_USER_AGENT}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    profile_path = Path(user_data_dir) if user_data_dir else _profile_dir()
    _clean_stale_chrome_locks(profile_path)
    options.add_argument(f"--user-data-dir={profile_path}")

    chrome_bin = _bundled_chrome_binary()
    driver_bin = _bundled_chromedriver()

    if chrome_bin and driver_bin:
        options.binary_location = str(chrome_bin)
        service = Service(executable_path=str(driver_bin))
        driver = webdriver.Chrome(service=service, options=options)
    else:
        sys_driver = _system_chromedriver()
        if sys_driver:
            service = Service(executable_path=sys_driver)
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )
    except Exception:
        pass
    return driver
