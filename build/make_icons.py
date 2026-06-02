"""Convert logo.png into macOS .icns and Windows .ico for PyInstaller.

Usage:  python build/make_icons.py
Outputs:
  build/icons/icon.icns   (macOS bundle icon)
  build/icons/icon.ico    (Windows exe icon)
  build/icons/icon.png    (cropped square master, used by GUI window icon)
"""
from __future__ import annotations
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "logo.png"
OUT_DIR = ROOT / "build" / "icons"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _remove_white_background(img: Image.Image, threshold: int = 235) -> Image.Image:
    """Flood-fill the outer white region to transparent, leaving inner white
    (inside the circle, e.g. the ticket cutout) intact."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    arr = np.array(img)
    rgb = arr[:, :, :3]
    is_whitish = np.all(rgb >= threshold, axis=2).astype(np.uint8) * 255

    h, w = is_whitish.shape
    # Pad mask by 1px so floodFill can seed safely
    flood_mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    filled = is_whitish.copy()

    # Seed from every corner; whichever ones are white-ish get filled.
    seeded = False
    for sx, sy in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        if is_whitish[sy, sx] == 255:
            cv2.floodFill(filled, flood_mask.copy(), (sx, sy), 128)
            seeded = True
    if not seeded:
        return img  # nothing to remove

    outer_bg = filled == 128
    # Soften edge by 1px to hide flood-fill aliasing
    soft = cv2.dilate(outer_bg.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=1)
    soft = cv2.GaussianBlur(soft, (3, 3), 0)
    arr[..., 3] = np.where(outer_bg, 0, arr[..., 3])
    # Apply soft alpha at edges
    edge = (soft > 0) & ~outer_bg
    arr[edge, 3] = np.minimum(arr[edge, 3], 255 - soft[edge]).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _autocrop_square(img: Image.Image) -> Image.Image:
    """Crop transparent borders (after background removal) then pad to square."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # Use alpha channel to find content bbox.
    alpha = img.split()[-1]
    bbox = alpha.getbbox()
    if bbox:
        img = img.crop(bbox)

    w, h = img.size
    side = max(w, h)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return square


def make_icns(master: Image.Image, dest: Path) -> None:
    """Build a .icns using macOS's iconutil if available; else fallback to PIL .icns."""
    iconset = OUT_DIR / "icon.iconset"
    if iconset.exists():
        shutil.rmtree(iconset)
    iconset.mkdir(parents=True)
    spec = [
        (16, "icon_16x16.png", False),
        (32, "icon_16x16@2x.png", True),
        (32, "icon_32x32.png", False),
        (64, "icon_32x32@2x.png", True),
        (128, "icon_128x128.png", False),
        (256, "icon_128x128@2x.png", True),
        (256, "icon_256x256.png", False),
        (512, "icon_256x256@2x.png", True),
        (512, "icon_512x512.png", False),
        (1024, "icon_512x512@2x.png", True),
    ]
    for size, name, _ in spec:
        master.resize((size, size), Image.LANCZOS).save(iconset / name, "PNG")

    if shutil.which("iconutil"):
        subprocess.check_call(
            ["iconutil", "-c", "icns", str(iconset), "-o", str(dest)]
        )
    else:
        # cross-platform fallback (smaller variety)
        master.save(dest, format="ICNS")
    shutil.rmtree(iconset, ignore_errors=True)


def make_ico(master: Image.Image, dest: Path) -> None:
    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    master.save(dest, format="ICO", sizes=sizes)


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        return 1
    print(f"[make_icons] source: {SRC}")
    img = Image.open(SRC)
    img = _remove_white_background(img)
    master = _autocrop_square(img).resize((1024, 1024), Image.LANCZOS)

    png_master = OUT_DIR / "icon.png"
    master.save(png_master, "PNG")
    print(f"[make_icons] wrote {png_master}")

    icns = OUT_DIR / "icon.icns"
    make_icns(master, icns)
    print(f"[make_icons] wrote {icns}  ({icns.stat().st_size // 1024} KB)")

    ico = OUT_DIR / "icon.ico"
    make_ico(master, ico)
    print(f"[make_icons] wrote {ico}  ({ico.stat().st_size // 1024} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
