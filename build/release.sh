#!/usr/bin/env bash
# One-shot release: bump version.json -> commit -> push -> tag -> push tag.
# Pushing the tag triggers .github/workflows/release.yml which auto-builds
# Mac arm64 / Mac Intel / Windows x64 and creates a GitHub Release with all three zips.
#
# Usage:
#   ./build/release.sh v0.2.1
#   ./build/release.sh v0.2.1 "fix singleton lock + new icon"
set -euo pipefail

VERSION="${1:-}"
NOTES="${2:-Release ${VERSION}}"

if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version> [commit message]" >&2
    echo "Example: $0 v0.2.1 'fix singleton lock + new icon'" >&2
    exit 1
fi
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
    echo "ERROR: version must be vX.Y.Z (got: $VERSION)" >&2
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -n "$(git status --porcelain | grep -E '\.env$|secret|private_key' || true)" ]]; then
    echo "ERROR: detected potential secret in working tree; aborting" >&2
    exit 1
fi

VER_PLAIN="${VERSION#v}"
python3 - "$VER_PLAIN" <<'PY'
import json, sys
v = sys.argv[1]
with open("version.json", encoding="utf-8") as f:
    data = json.load(f)
data["version"] = v
with open("version.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"version.json -> {v}")
PY

git add -A
git commit -m "$NOTES" || echo "(nothing to commit; using existing HEAD)"
git push origin "$(git rev-parse --abbrev-ref HEAD)"

if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "ERROR: tag $VERSION already exists locally" >&2
    exit 1
fi
if git ls-remote --tags origin "$VERSION" | grep -q "$VERSION"; then
    echo "ERROR: tag $VERSION already exists on remote" >&2
    exit 1
fi

git tag -a "$VERSION" -m "$NOTES"
git push origin "$VERSION"

REPO_URL="$(git remote get-url origin | sed -E 's|^git@github.com:|https://github.com/|; s|\.git$||')"
echo
echo "✅ Pushed tag $VERSION"
echo
echo "📺 Watch the build:  ${REPO_URL}/actions"
echo "📦 Release page:     ${REPO_URL}/releases/tag/${VERSION}"
echo
echo "預估 8-12 分鐘後三平台 zip (Mac arm64 / Mac Intel / Windows x64) 會自動上架。"
echo "之後使用者開啟舊版 App, 啟動時會跳出 '發現新版本' 對話框。"
