#!/usr/bin/env bash
# Build TixCraft.app and zip it into dist/.
# Usage:  ./build/build_mac.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3.10 -m venv .venv || python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements-dev.txt

# Download Chrome for Testing + chromedriver for the host platform.
python build/fetch_chrome.py

APP_BUNDLE="準點搶.app"
rm -rf build/work "dist/TixCraft" "dist/${APP_BUNDLE}"
pyinstaller --noconfirm --clean --workpath build/work --distpath dist build/tixcraft.spec

# Copy bundled Chrome into the .app after PyInstaller (avoids osx.py walking it).
ARCH="$(uname -m)"
if [[ "$ARCH" == "arm64" ]]; then
  PLAT="mac-arm64"
else
  PLAT="mac-x64"
fi
CHROME_SRC="assets/chrome/${PLAT}"
CHROME_DST="dist/${APP_BUNDLE}/Contents/Resources/assets/chrome/${PLAT}"
if [[ ! -d "$CHROME_SRC" ]]; then
  echo "ERROR: $CHROME_SRC missing; run python build/fetch_chrome.py first." >&2
  exit 1
fi
mkdir -p "$(dirname "$CHROME_DST")"
cp -R "$CHROME_SRC" "$CHROME_DST"
xattr -dr com.apple.quarantine "dist/${APP_BUNDLE}" 2>/dev/null || true

cd dist
if [[ -d "${APP_BUNDLE}" ]]; then
  zip -qry "準點搶-mac-${ARCH}.zip" "${APP_BUNDLE}"
  echo
  echo "Built: dist/${APP_BUNDLE}"
  echo "Zip:   dist/準點搶-mac-${ARCH}.zip"
fi
