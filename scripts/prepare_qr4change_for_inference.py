"""Shrink the QR4Change dump images for upload to Colab as bootstrap-detector input.

YOLO boxes are normalised 0..1, so a prediction made on a resized copy still applies
correctly to the original, full-resolution image in Label Studio - only the pixels fed
to the detector get smaller, not the coordinate system. Capping the long edge at 1280 px
cuts the 3.5 GB source folder to a size a browser can upload to Colab without a Drive
mount. The exact duplicate (IMG 710, see manifest.csv) is skipped.

Output: data/bootstrap/qr4_infer/<item_id>.jpg, item_id matching the manifest
(e.g. qr4-1 for "IMG (1).jpg"), so predictions can be matched back to Label Studio tasks
by item_id alone.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/public/qr4change/Urban Civic Issues Image Dataset Potholes and Garb/garbage/yes"
OUT = ROOT / "data/bootstrap/qr4_infer"
MAX_EDGE = 1280
SKIP_NUMBERS = {710}  # exact duplicate of IMG (709).jpg


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    written = 0
    for image_path in sorted(SRC.iterdir()):
        if image_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        match = re.search(r"\((\d+)\)", image_path.name)
        if not match or int(match.group(1)) in SKIP_NUMBERS:
            continue
        item_id = f"qr4-{match.group(1)}"

        with Image.open(image_path) as img:
            img = img.convert("RGB")
            scale = MAX_EDGE / max(img.size)
            if scale < 1.0:
                img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
            img.save(OUT / f"{item_id}.jpg", "JPEG", quality=85)
        written += 1
        if written % 100 == 0:
            print(f"resized {written}")

    print(f"Wrote {written} resized images to {OUT}")


if __name__ == "__main__":
    main()
