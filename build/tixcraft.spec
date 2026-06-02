# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — produces 準點搶.app on macOS (folder bundle) and
# 準點搶.exe on Windows (single-file with embedded Chrome).
# Run from the project root:  pyinstaller build/tixcraft.spec
from __future__ import annotations
import os
import platform
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent  # noqa: F821  SPECPATH provided by PyInstaller
APP_NAME = "TixCraft"
DISPLAY_NAME = "準點搶"

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def _chrome_platform_dir() -> str:
    if sys.platform == "darwin":
        return "mac-arm64" if platform.machine().lower() in ("arm64", "aarch64") else "mac-x64"
    if sys.platform.startswith("win"):
        return "win64"
    return "linux64"


block_cipher = None

datas = []
# ddddocr ships .onnx models that PyInstaller doesn't auto-detect.
datas += collect_data_files("ddddocr", include_py_files=False)
# Bundle our own seed config + version metadata + icon.
datas += [
    (str(PROJECT_ROOT / "config_sample.json"), "."),
    (str(PROJECT_ROOT / "version.json"), "."),
    (str(PROJECT_ROOT / "build" / "icons" / "icon.png"), "."),
]

ICON_ICNS = str(PROJECT_ROOT / "build" / "icons" / "icon.icns")
ICON_ICO = str(PROJECT_ROOT / "build" / "icons" / "icon.ico")

# Chrome for Testing handling differs per platform:
#   macOS: PyInstaller's osx.py crashes when walking the nested Chrome.app, so
#          the build script copies the Chrome tree into Contents/Resources AFTER
#          PyInstaller finishes (see build/build_mac.sh).
#   Win:   Chrome on Windows is a plain folder, no .app weirdness. We embed it
#          directly via datas so the resulting .exe is truly self-contained.
if IS_WIN:
    win_chrome = PROJECT_ROOT / "assets" / "chrome" / "win64"
    if not win_chrome.exists():
        raise SystemExit(
            "assets/chrome/win64 missing; run `python build/fetch_chrome.py "
            "--platform win64` first."
        )
    for root_dir, _dirs, files in os.walk(win_chrome):
        for fname in files:
            src = Path(root_dir) / fname
            rel_dir = src.parent.relative_to(PROJECT_ROOT)
            datas.append((str(src), str(rel_dir).replace("\\", "/")))

hiddenimports = []
hiddenimports += collect_submodules("onnxruntime")
hiddenimports += collect_submodules("ddddocr")
hiddenimports += collect_submodules("selenium")
hiddenimports += collect_submodules("webdriver_manager")
hiddenimports += collect_submodules("trio")
hiddenimports += collect_submodules("trio_websocket")
hiddenimports += [
    "PIL._tkinter_finder",
]

a = Analysis(
    [str(PROJECT_ROOT / "gui.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pytest", "torch", "torchvision"],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if IS_WIN:
    # --- Windows: single-file .exe with Chrome embedded. ---
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name=DISPLAY_NAME,                # outputs "準點搶.exe"
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        runtime_tmpdir=None,              # default %TEMP%\_MEIxxxx extraction
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_ICO,
    )
else:
    # --- macOS: standard --onedir + .app bundle (BUNDLE wraps it nicely). ---
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=APP_NAME,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=ICON_ICNS,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        upx_exclude=[],
        name=APP_NAME,
    )
    app = BUNDLE(
        coll,
        name=f"{DISPLAY_NAME}.app",
        icon=ICON_ICNS,
        bundle_identifier="tw.haoyi.zhundian",
        info_plist={
            "CFBundleName": DISPLAY_NAME,
            "CFBundleDisplayName": DISPLAY_NAME,
            "NSHumanReadableCopyright": "© 2026 浩毅科技 HaoYi Tech",
            "CFBundleShortVersionString": "0.2.0",
            "CFBundleVersion": "0.2.0",
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSRequiresAquaSystemAppearance": False,
        },
    )
