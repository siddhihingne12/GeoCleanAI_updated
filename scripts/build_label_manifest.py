"""Build the labelling manifest and Label Studio import files (scope decision E + A).

Every candidate image from the public sources and the Pune Mapillary review gets one
manifest row recording source, licence, split group, status and suggested class, with
an exclusion reason where it is left out. Images that need labelling are written as
Label Studio tasks, one file per source; existing Roboflow boxes for the matching class
are attached as predictions so they can be corrected rather than redrawn.

Split groups come from Group-NearDuplicates.ps1 reports (public sets) and Mapillary
sequence IDs (Pune). Assign whole groups, never single images, to train, validation or
test. Pune Mapillary images are a diagnostic set only and never enter training.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
QR4_DIR = ROOT / "data/public/qr4change/Urban Civic Issues Image Dataset Potholes and Garb/garbage"
OVERFLOW_DIR = ROOT / "data/public/roboflow/garbage_can_overflow/v4-yolov8"
PILES_DIR = ROOT / "data/public/roboflow/piles_of_garbage/v1-yolov8"
DSOELMA_DIR = ROOT / "data/public/roboflow/garbage_dsoelma/v6-yolov8"
REVIEW_DIR = ROOT / "reports/visual-review"
GROUP_REPORTS = ROOT / "reports/public-datasets"
MANIFEST_DIR = ROOT / "reports/labelling"
TASK_DIR = ROOT / "data/labelling"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
STOCK = re.compile(r"getty|shutterstock|istock|alamy|dreamstime|depositphotos|adobestock|123rf", re.I)
PRE_AUGMENTED = re.compile(r"gridmask|blur|mosaic|cutout|noise", re.I)
# Three consecutive capture segments on 3 August 2025 show one hanging street bin
# spilling onto the ground (dataset review, QR4Change segment review).
QR4_OVERFLOW_NUMBERS = set(range(6, 21))
OVERFLOW_CLASS = "Trash over flow"
PILE_CLASS = "1"

FIELDS = ["item_id", "source", "licence", "file", "split_group", "status",
          "suggested_class", "exclusion_reason", "prefill_boxes", "notes"]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_groups(report_name: str, prefix: str) -> dict[str, str]:
    """Map image path (relative to the grouped folder, posix) to a namespaced group."""
    report = json.loads((GROUP_REPORTS / f"{report_name}-groups.json").read_text(encoding="utf-8-sig"))
    return {item["file"].replace("\\", "/"): f"{prefix}:{item['group']}" for item in report["image_list"]}


def read_names(yolo_dir: Path) -> list[str]:
    text = (yolo_dir / "data.yaml").read_text(encoding="utf-8")
    match = re.search(r"names:\s*\[(.*?)\]", text)
    if not match:
        raise ValueError(f"cannot read class names from {yolo_dir / 'data.yaml'}")
    return [n.strip().strip("'\"") for n in match.group(1).split(",")]


def read_yolo(yolo_dir: Path):
    """Yield (image path, [(class index, x1, y1, x2, y2)]) with normalised corners."""
    for images in sorted(yolo_dir.glob("*/images")):
        labels = images.parent / "labels"
        for image in sorted(p for p in images.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS):
            boxes = []
            label = labels / f"{image.stem}.txt"
            if label.exists():
                for line in label.read_text(encoding="utf-8").splitlines():
                    parts = line.split()
                    if len(parts) < 5:
                        continue
                    values = [float(v) for v in parts[1:]]
                    if len(values) == 4:
                        cx, cy, w, h = values
                        corners = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                    else:
                        xs, ys = values[0::2], values[1::2]
                        corners = (min(xs), min(ys), max(xs), max(ys))
                    boxes.append((int(parts[0]), *(min(1.0, max(0.0, c)) for c in corners)))
            yield image, boxes


def ls_prediction(boxes, label: str) -> list[dict]:
    result = []
    for i, (_, x1, y1, x2, y2) in enumerate(boxes):
        result.append({
            "id": f"prefill{i}", "from_name": "label", "to_name": "image", "type": "rectanglelabels",
            "value": {"x": x1 * 100, "y": y1 * 100, "width": (x2 - x1) * 100, "height": (y2 - y1) * 100,
                      "rotation": 0, "rectanglelabels": [label]},
        })
    return [{"model_version": "roboflow-import", "result": result}] if result else []


def row(item_id, source, licence, path, group, status, suggested="", reason="", boxes=0, notes=""):
    return {"item_id": item_id, "source": source, "licence": licence, "file": rel(path),
            "split_group": group, "status": status, "suggested_class": suggested,
            "exclusion_reason": reason, "prefill_boxes": boxes, "notes": notes}


def build():
    rows: list[dict] = []
    tasks: dict[str, list[dict]] = defaultdict(list)

    def add_task(name, r, predictions=()):
        tasks[name].append({
            "data": {"image": "/data/local-files/?d=" + quote(r["file"], safe="/"),
                     "item_id": r["item_id"], "source": r["source"],
                     "split_group": r["split_group"], "suggested_class": r["suggested_class"]},
            "predictions": list(predictions),
        })

    # QR4Change dump folder: Pune phone photos, no boxes.
    qr4_groups = load_groups("qr4change_dumps", "qr4")
    for image in sorted((QR4_DIR / "yes").iterdir()):
        if image.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        number = int(re.search(r"\((\d+)\)", image.name).group(1))
        item = f"qr4-{number}"
        group = qr4_groups.get(image.name, "")
        if number == 710:
            rows.append(row(item, "qr4change", "CC BY 4.0", image, group, "excluded",
                            reason="exact duplicate of IMG (709).jpg"))
            continue
        suggested = "overflowing_bin" if number in QR4_OVERFLOW_NUMBERS else "roadside_dump"
        r = row(item, "qr4change", "CC BY 4.0", image, group, "to_label", suggested,
                notes="" if group else "no EXIF capture time; grouped by visual similarity only")
        rows.append(r)
        add_task("qr4change", r)
    for image in sorted((QR4_DIR / "no").iterdir()):
        if image.suffix.lower() in IMAGE_EXTENSIONS:
            rows.append(row(f"qr4no-{image.stem}", "qr4change", "CC BY 4.0", image, "", "excluded",
                            reason="non-garbage folder: mixed web imagery, apparently including Google Street View-derived bins"))

    # Roboflow garbage can overflow: keep "Trash over flow" images for review and re-boxing.
    names = read_names(OVERFLOW_DIR)
    overflow_idx = names.index(OVERFLOW_CLASS)
    groups = load_groups("overflow_groups", "ovf")
    for image, boxes in read_yolo(OVERFLOW_DIR):
        key = image.resolve().relative_to(OVERFLOW_DIR.resolve()).as_posix()
        item = f"ovf-{image.parent.parent.name}-{image.stem[:40]}"
        group = groups.get(key, "")
        target = [b for b in boxes if b[0] == overflow_idx]
        base = ("roboflow_garbage_can_overflow", "CC BY 4.0", image, group)
        if STOCK.search(image.name):
            rows.append(row(item, *base, "excluded", reason="stock photo; uploader cannot relicense"))
        elif PRE_AUGMENTED.search(image.name):
            rows.append(row(item, *base, "excluded", reason="pre-augmented copy"))
        elif target:
            r = row(item, *base, "to_label", "overflowing_bin", boxes=len(target),
                    notes="source class 'Trash over flow' is broader than overflowing_bin; review and re-box")
            rows.append(r)
            add_task("overflow", r, ls_prediction(target, "overflowing_bin"))
        elif boxes:
            rows.append(row(item, *base, "optional_negative",
                            notes="bin classes only; mostly dumpster close-ups and product shots"))
        else:
            rows.append(row(item, *base, "excluded", reason="no boxes in source export"))

    # Roboflow piles of garbage: class "1" piles; class "2" is studio bottle close-ups.
    names = read_names(PILES_DIR)
    pile_idx = names.index(PILE_CLASS)
    groups = load_groups("piles_groups", "pil")
    for image, boxes in read_yolo(PILES_DIR):
        key = image.resolve().relative_to(PILES_DIR.resolve()).as_posix()
        item = f"pil-{image.parent.parent.name}-{image.stem[:40]}"
        target = [b for b in boxes if b[0] == pile_idx]
        base = ("roboflow_piles_of_garbage", "CC BY 4.0", image, groups.get(key, ""))
        if target:
            r = row(item, *base, "to_label", "roadside_dump", boxes=len(target),
                    notes="drop boxes around single wrappers; keep concentrated piles")
            rows.append(r)
            add_task("piles", r, ls_prediction(target, "roadside_dump"))
        else:
            rows.append(row(item, *base, "excluded", reason="bottle close-up class only"))

    # Roboflow dsoelma: one Russian container site, labels do not match, personal data overlay.
    for image, _ in read_yolo(DSOELMA_DIR):
        rows.append(row(f"dso-{image.parent.parent.name}-{image.stem[:40]}", "roboflow_garbage_dsoelma",
                        "CC BY 4.0", image, "", "excluded",
                        reason="single site; labels do not match project classes; overlay names crew and shows plates"))

    # Pune Mapillary review: diagnostic positives and hard negatives, never training.
    seen = set()
    for folder in sorted(p for p in REVIEW_DIR.iterdir() if p.is_dir()):
        notes_path, manifest_path = folder / "review-notes.json", folder / "manifest.json"
        if not (notes_path.exists() and manifest_path.exists()):
            continue
        manifest = {str(m["image_id"]): m for m in json.loads(manifest_path.read_text(encoding="utf-8-sig"))}
        for note in json.loads(notes_path.read_text(encoding="utf-8-sig")):
            finding, image_id = note.get("finding"), str(note.get("image_id"))
            if finding not in ("roadside_dump_positive", "hard_negative_candidate") or image_id in seen:
                continue
            meta = manifest.get(image_id)
            if not meta or not (folder / meta["file"]).exists():
                continue
            seen.add(image_id)
            positive = finding == "roadside_dump_positive"
            r = row(f"mly-{image_id}", "mapillary_pune", "CC BY-SA 4.0", folder / meta["file"],
                    f"mly:{meta['sequence_id']}",
                    "pune_diagnostic_positive" if positive else "pune_diagnostic_negative",
                    "roadside_dump" if positive else "", notes=note.get("note", "")[:200])
            rows.append(r)
            add_task("pune-diagnostic", r)

    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    with (MANIFEST_DIR / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    task_counts = {}
    for name, items in tasks.items():
        # Put the first image of every group ahead of second images, so that labelling
        # stopped at any point still covers as many distinct scenes as possible.
        rank = Counter()
        ordered = []
        for t in items:
            group = t["data"]["split_group"] or t["data"]["item_id"]
            ordered.append((rank[group], t))
            rank[group] += 1
        ordered.sort(key=lambda pair: pair[0])
        (TASK_DIR / f"tasks-{name}.json").write_text(json.dumps([t for _, t in ordered], indent=1), encoding="utf-8")
        task_counts[name] = len(items)

    summary = {
        "rows": len(rows),
        "by_source_and_status": dict(sorted(Counter(f"{r['source']} | {r['status']}" for r in rows).items())),
        "to_label_by_class": dict(Counter(r["suggested_class"] for r in rows if r["status"] == "to_label")),
        "to_label_split_groups_by_source": {
            s: len({r["split_group"] for r in rows if r["source"] == s and r["status"] == "to_label" and r["split_group"]})
            for s in sorted({r["source"] for r in rows if r["status"] == "to_label"})
        },
        "exclusion_reasons": dict(Counter(r["exclusion_reason"] for r in rows if r["exclusion_reason"])),
        "prefilled_boxes": sum(r["prefill_boxes"] for r in rows),
        "task_files": task_counts,
    }
    (MANIFEST_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    build()
