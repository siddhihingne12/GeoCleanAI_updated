"""Build a small 2-class YOLO dataset for a bootstrap detector, trained on Colab.

Source: the same "to_label" images build_label_manifest.py selected from the two
Roboflow sets that already carry real boxes (garbage_can_overflow "Trash over flow"
and piles_of_garbage class "1"), remapped to the project's two classes:
  0 = roadside_dump   (from piles_of_garbage class "1")
  1 = overflowing_bin (from garbage_can_overflow "Trash over flow")

This bootstrap model is not the final detector — its only job is to pre-label the 707
QR4Change images, which have no boxes at all, so a person corrects boxes instead of
drawing every one from scratch. Split groups (from Group-NearDuplicates.ps1) are kept
whole in one split, so a near-duplicate frame never leaks between train and val.

Images are copied, not moved or symlinked, so the original Roboflow export is
untouched. Output: data/bootstrap/{images,labels}/{train,val}/, data/bootstrap/data.yaml.
"""
from __future__ import annotations

import random
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_label_manifest as m  # noqa: E402

OUT = m.ROOT / "data/bootstrap"
VAL_FRACTION = 0.15
SEED = 20260913  # fixed so reruns reproduce the same split
CLASSES = ["roadside_dump", "overflowing_bin"]


def assign_split(group_ids: set[str]) -> dict[str, str]:
    """Deterministically assign whole groups to train/val by a shuffled, seeded order."""
    ordered = sorted(group_ids)
    random.Random(SEED).shuffle(ordered)
    cut = max(1, round(len(ordered) * (1 - VAL_FRACTION)))
    return {g: "train" for g in ordered[:cut]} | {g: "val" for g in ordered[cut:]}


def collect(yolo_dir: Path, class_idx: int, out_class: int, group_prefix: str):
    """Yield (image path, item_id, group, [(out_class, x1, y1, x2, y2), ...])."""
    groups = m.load_groups(
        "overflow_groups" if group_prefix == "ovf" else "piles_groups", group_prefix
    )
    for image, boxes in m.read_yolo(yolo_dir):
        key = image.resolve().relative_to(yolo_dir.resolve()).as_posix()
        target = [(out_class, x1, y1, x2, y2) for cls, x1, y1, x2, y2 in boxes if cls == class_idx]
        if not target:
            continue
        if m.STOCK.search(image.name) or m.PRE_AUGMENTED.search(image.name):
            continue
        item_id = f"{group_prefix}-{image.parent.parent.name}-{image.stem[:40]}"
        group = groups.get(key, item_id)  # ungrouped images are their own singleton group
        yield image, item_id, group, target


def main():
    if OUT.exists():
        shutil.rmtree(OUT)

    overflow_names = m.read_names(m.OVERFLOW_DIR)
    piles_names = m.read_names(m.PILES_DIR)
    items = list(collect(m.PILES_DIR, piles_names.index(m.PILE_CLASS), 0, "pil"))
    items += list(collect(m.OVERFLOW_DIR, overflow_names.index(m.OVERFLOW_CLASS), 1, "ovf"))

    splits = assign_split({group for _, _, group, _ in items})

    counts = {"train": [0, 0], "val": [0, 0]}
    for image, item_id, group, boxes in items:
        split = splits[group]
        (OUT / "images" / split).mkdir(parents=True, exist_ok=True)
        (OUT / "labels" / split).mkdir(parents=True, exist_ok=True)
        dest_image = OUT / "images" / split / f"{item_id}{image.suffix.lower()}"
        shutil.copyfile(image, dest_image)
        lines = []
        for cls, x1, y1, x2, y2 in boxes:
            cx, cy, w, h = (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y2 - y1
            lines.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            counts[split][cls] += 1
        (OUT / "labels" / split / f"{item_id}.txt").write_text("\n".join(lines), encoding="utf-8")

    # No "path:" key: Ultralytics then anchors train/val to the yaml file's own
    # directory. A literal "path: ." instead resolves against the *process's* working
    # directory, which is /content in Colab, not /content/dataset - it then looks for
    # /content/images/val and fails.
    (OUT / "data.yaml").write_text(
        "train: images/train\nval: images/val\n"
        f"names: [{', '.join(repr(c) for c in CLASSES)}]\n",
        encoding="utf-8",
    )

    n_train = len(list((OUT / "images/train").iterdir())) if (OUT / "images/train").exists() else 0
    n_val = len(list((OUT / "images/val").iterdir())) if (OUT / "images/val").exists() else 0
    print(f"train images: {n_train}  (roadside_dump boxes {counts['train'][0]}, overflowing_bin boxes {counts['train'][1]})")
    print(f"val images:   {n_val}  (roadside_dump boxes {counts['val'][0]}, overflowing_bin boxes {counts['val'][1]})")
    print(f"groups: train {sum(1 for v in splits.values() if v == 'train')}, "
          f"val {sum(1 for v in splits.values() if v == 'val')}")
    print(f"Wrote dataset to {OUT}")


if __name__ == "__main__":
    main()
