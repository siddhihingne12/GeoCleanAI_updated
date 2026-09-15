"""Export "GeoClean training" annotations to a group-disjoint YOLO dataset.

Pulls the annotated tasks straight from Label Studio's JSON export, so the decision,
item_id, split_group and task meta all survive. For each task, the newest annotation that
was not cancelled is used:
  - keep with at least one box -> image + YOLO label file
  - hard_negative              -> image + empty label file
  - reject_* or no decision    -> left out

Whole split groups go to one split (seeded shuffle, 70/15/15 by group), so near-duplicate
frames never cross train, val and test. Images are copied, never moved; any image with a
long edge over MAX_EDGE is saved as a smaller JPEG. YOLO boxes are normalised, so labels
are unchanged, and training at 640 px loses nothing. The QR4Change originals (about 5 MB
each) would otherwise make the Colab upload over 1 GB. None of those photos carries an EXIF
rotation, so resizing does not move pixels relative to the boxes.

Output: data/dataset/{images,labels}/{train,val,test}/, data/dataset/data.yaml,
data/dataset/provenance.csv, and data/zips/geoclean_dataset.zip for
notebooks/geoclean_train.ipynb. provenance.csv records each image's label origin:
meta.label_origin from auto_label.py, or "human" when the task has none. The folder and
zip are rebuilt from scratch on every run.
"""
from __future__ import annotations

import collections
import csv
import random
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup_label_studio_projects as s  # noqa: E402

PROJECT_TITLE = "GeoClean training"
OUT = s.ROOT / "data/dataset"
ZIP = s.ROOT / "data/zips/geoclean_dataset.zip"
SEED = 20260913  # same seed as the bootstrap split, so reruns reproduce the same split
FRACTIONS = {"train": 0.70, "val": 0.15}  # test gets the remainder
CLASSES = ["roadside_dump", "overflowing_bin"]
MAX_EDGE = 1280


def assign_split(group_ids: set[str]) -> dict[str, str]:
    ordered = sorted(group_ids)
    random.Random(SEED).shuffle(ordered)
    train_cut = round(len(ordered) * FRACTIONS["train"])
    val_cut = train_cut + round(len(ordered) * FRACTIONS["val"])
    return ({g: "train" for g in ordered[:train_cut]}
            | {g: "val" for g in ordered[train_cut:val_cut]}
            | {g: "test" for g in ordered[val_cut:]})


def image_path(url: str) -> Path:
    # Tasks point at Label Studio's local-files endpoint: /data/local-files/?d=<repo-relative path>
    return s.ROOT / parse_qs(urlparse(url).query)["d"][0]


def copy_image(src: Path, dest_stem: Path) -> Path:
    """Copy src, shrinking it to MAX_EDGE on the long edge when larger. Returns the written path."""
    # Append the extension as text: item_ids contain dots (ovf-train--100_jpg.rf.2925e2...),
    # and Path.with_suffix would treat everything after the last dot as the old extension.
    with Image.open(src) as img:
        if max(img.size) <= MAX_EDGE:
            dest = dest_stem.parent / f"{dest_stem.name}{src.suffix.lower()}"
            shutil.copyfile(src, dest)
            return dest
        scale = MAX_EDGE / max(img.size)
        dest = dest_stem.parent / f"{dest_stem.name}.jpg"
        img.convert("RGB").resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS) \
            .save(dest, "JPEG", quality=90)
        return dest


def read_annotation(task: dict):
    """Return (decision, [(class_idx, cx, cy, w, h), ...]) from the newest live annotation."""
    live = [a for a in task["annotations"] if not a.get("was_cancelled")]
    if not live:
        return None, []
    annotation = max(live, key=lambda a: (a.get("updated_at") or "", a["id"]))
    decision, boxes = None, []
    for r in annotation["result"]:
        if r["type"] == "choices" and r["from_name"] == "decision":
            decision = r["value"]["choices"][0]
        elif r["type"] == "rectanglelabels":
            v = r["value"]
            x1, y1 = max(0.0, v["x"] / 100), max(0.0, v["y"] / 100)
            x2, y2 = min(1.0, (v["x"] + v["width"]) / 100), min(1.0, (v["y"] + v["height"]) / 100)
            if x2 > x1 and y2 > y1:
                boxes.append((CLASSES.index(v["rectanglelabels"][0]), (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1))
    return decision, boxes


def write_zip() -> None:
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    # Stored, not deflated: the JPEGs are already compressed. Forward slashes so Colab's
    # Linux side recreates the folders.
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_STORED) as z:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(OUT).as_posix())
    print(f"Wrote {ZIP} ({ZIP.stat().st_size / 1e6:.0f} MB)")


def main() -> None:
    project = s.find_project(PROJECT_TITLE)
    if project is None:
        sys.exit(f'Project "{PROJECT_TITLE}" not found.')
    tasks = s.call("GET", f"/api/projects/{project['id']}/export?exportType=JSON")

    items, left_out = [], collections.Counter()
    for task in tasks:
        decision, boxes = read_annotation(task)
        if decision == "keep" and not boxes:
            left_out["keep without boxes"] += 1
            continue
        if decision not in ("keep", "hard_negative"):
            left_out[decision or "no decision"] += 1
            continue
        image = image_path(task["data"]["image"])
        if not image.exists():
            left_out["image file missing"] += 1
            continue
        items.append((task, decision, [] if decision == "hard_negative" else boxes, image))
    if not items:
        sys.exit("No keep or hard_negative annotations to export.")

    if OUT.exists():
        shutil.rmtree(OUT)
    splits = assign_split({t["data"]["split_group"] for t, _, _, _ in items})
    used_names: set[str] = set()
    counts = collections.defaultdict(collections.Counter)
    rows = []
    resized = 0
    for task, decision, boxes, image in items:
        split = splits[task["data"]["split_group"]]
        name = task["data"]["item_id"]
        if name in used_names:
            name = f"{name}-t{task['id']}"
        used_names.add(name)
        for kind in ("images", "labels"):
            (OUT / kind / split).mkdir(parents=True, exist_ok=True)
        with Image.open(image) as img:
            resized += max(img.size) > MAX_EDGE
        copy_image(image, OUT / "images" / split / name)
        (OUT / "labels" / split / f"{name}.txt").write_text(
            "\n".join(f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for c, cx, cy, w, h in boxes), encoding="utf-8")

        origin = (task.get("meta") or {}).get("label_origin", "human")
        per_class = collections.Counter(CLASSES[c] for c, *_ in boxes)
        counts[split]["images"] += 1
        counts[split][decision] += 1
        counts[split].update(per_class)
        counts[split][f"origin {origin}"] += 1
        rows.append({"item_id": task["data"]["item_id"], "file": name, "source": task["data"].get("source"),
                     "split_group": task["data"]["split_group"], "split": split, "decision": decision,
                     "origin": origin, **{c: per_class[c] for c in CLASSES}})

    # No "path:" key: Ultralytics then resolves these folders against this yaml's directory.
    (OUT / "data.yaml").write_text(
        "train: images/train\nval: images/val\ntest: images/test\n"
        f"names: [{', '.join(repr(c) for c in CLASSES)}]\n", encoding="utf-8")
    with open(OUT / "provenance.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["split"], r["item_id"])))

    for split in ("train", "val", "test"):
        c = counts[split]
        extra = ", ".join(f"{k} {v}" for k, v in sorted(c.items()) if k.startswith("origin"))
        print(f"{split}: {c['images']} images ({c['keep']} keep, {c['hard_negative']} hard_negative); "
              f"boxes roadside_dump {c['roadside_dump']}, overflowing_bin {c['overflowing_bin']}; {extra}")
    for reason, count in sorted(left_out.items()):
        print(f"Left out ({reason}): {count}")
    print(f"Images shrunk to a {MAX_EDGE} px long edge: {resized}")
    auto = sum(1 for r in rows if r["origin"] != "human")
    if auto:
        print(f"Note: {auto} of {len(rows)} images carry unreviewed automatic labels, including in val and test.")
    print(f"Wrote {OUT}")
    write_zip()


if __name__ == "__main__":
    main()
