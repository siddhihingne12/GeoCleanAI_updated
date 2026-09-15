"""Accept the pre-filled boxes in "GeoClean training" as annotations, with no person reviewing them.

Chosen on 14 September 2026 to skip manual labelling. These labels are unreviewed:
Roboflow boxes use the sources' own class definitions, and bootstrap-detector boxes on
QR4Change are model guesses. Every task this script annotates gets
meta.label_origin = ORIGIN, so export_yolo_dataset.py can report how much of the
dataset is automatic, and a later review can find these tasks.

Rules:
  - Roboflow tasks: every pre-filled box is kept, decision "keep".
  - QR4Change tasks: "keep" only when *every* box scored >= --threshold (default 0.5).
    Weak boxes are not dropped from an otherwise kept image, because an unboxed real pile
    would teach the detector that piles are background.
  - Tasks with no boxes, or with any box below the threshold, stay unannotated. They are
    not marked hard_negative: the model may have missed a pile.

Safe to rerun: tasks that already have an annotation (automatic or human) are skipped.
Use --dry-run to print the counts without writing anything.
"""
from __future__ import annotations

import argparse
import collections
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_qr4_predictions as imp  # noqa: E402
import setup_label_studio_projects as s  # noqa: E402

ORIGIN = "auto-v1"
RETRIES = 5


def call_with_retry(method: str, path: str, body: dict):
    # Label Studio's SQLite backend occasionally fails a request with HTTP 500 ("Cannot
    # operate on a closed database"); s.call reports that by exiting, so catch and retry.
    for attempt in range(1, RETRIES + 1):
        try:
            return s.call(method, path, body)
        except SystemExit as err:
            if attempt == RETRIES:
                raise
            print(f"  retry {attempt}/{RETRIES - 1} after: {str(err)[:120]}", flush=True)
            time.sleep(5 * attempt)
            if method == "POST" and path.endswith("/annotations/"):
                task_path = path.removesuffix("annotations/")
                if s.call("GET", task_path).get("total_annotations", 0):
                    return None  # the failed request was saved after all; do not add a duplicate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="minimum confidence every bootstrap box on a QR4Change image must reach")
    parser.add_argument("--dry-run", action="store_true", help="print counts only")
    args = parser.parse_args()

    confidences = {item_id: [b["confidence"] for b in p["boxes"]] for item_id, p in imp.load_predictions().items()}
    project = s.find_project(imp.PROJECT_TITLE)
    if project is None:
        sys.exit(f'Project "{imp.PROJECT_TITLE}" not found. Run setup_label_studio_projects.py first.')
    tasks = s.call("GET", f"/api/projects/{project['id']}/export?exportType=JSON&download_all_tasks=true")
    # The export lists predictions only as ids, so fetch the full prediction objects separately.
    predictions = s.call("GET", f"/api/predictions/?project={project['id']}")
    predictions = predictions.get("results", predictions) if isinstance(predictions, dict) else predictions
    results_by_task = collections.defaultdict(list)
    for p in predictions:
        if p.get("model_version") == imp.PREFILL_TAG:
            results_by_task[p["task"]].extend(r for r in p["result"] if r["type"] == "rectanglelabels")

    plan, skipped = [], collections.Counter()
    for task in tasks:
        source = task["data"].get("source")
        if task["annotations"]:
            skipped["already annotated"] += 1
            continue
        boxes = results_by_task[task["id"]]
        if not boxes:
            skipped[f"{source}: no boxes"] += 1
            continue
        meta = {"label_origin": ORIGIN}
        if source == "qr4change":
            lowest = min(confidences.get(task["data"]["item_id"], [0.0]))
            if lowest < args.threshold:
                skipped[f"qr4change: a box below {args.threshold}"] += 1
                continue
            meta["min_confidence"] = lowest
        plan.append((task, boxes, meta))

    by_source = collections.Counter(t["data"].get("source") for t, _, _ in plan)
    by_class = collections.Counter(b["value"]["rectanglelabels"][0] for _, boxes, _ in plan for b in boxes)
    print(f"{'Would annotate' if args.dry_run else 'Annotating'} {len(plan)} tasks as keep: {dict(by_source)}")
    print(f"Boxes: {dict(by_class)}")
    for reason, count in sorted(skipped.items()):
        print(f"Left unannotated ({reason}): {count}")
    if args.dry_run:
        return

    for n, (task, boxes, meta) in enumerate(plan, 1):
        decision = {"from_name": "decision", "to_name": "image", "type": "choices", "value": {"choices": ["keep"]}}
        # Tag first: if the run dies between the two calls, the task is tagged but unannotated,
        # and a rerun annotates it. The other order would leave an untagged automatic label.
        call_with_retry("PATCH", f"/api/tasks/{task['id']}/", {"meta": (task.get("meta") or {}) | meta})
        call_with_retry("POST", f"/api/tasks/{task['id']}/annotations/", {"result": boxes + [decision], "lead_time": 0})
        if n % 50 == 0:
            print(f"  {n}/{len(plan)}", flush=True)
    print(f"Done. Tasks carry meta.label_origin = '{ORIGIN}': {s.BASE}/projects/{project['id']}/data")


if __name__ == "__main__":
    main()
