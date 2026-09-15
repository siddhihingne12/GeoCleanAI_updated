"""Push the Colab bootstrap detector's QR4Change predictions into Label Studio.

Reads data/bootstrap/qr4_predictions_result.zip (downloaded from
notebooks/geoclean_bootstrap_train.ipynb), matches each prediction's item_id to its
Label Studio task in the "GeoClean training" project, and imports the boxes as
starting predictions - editable, not final labels. Confidence is not filtered here;
low-confidence boxes are still worth a person's ten-second glance to reject.

Safe to rerun: existing predictions on a task are left as-is by Label Studio's import
endpoint, so it will not duplicate boxes if the same zip is imported twice, but it
will add a second copy if re-run against a *different* prediction file. If you need a
clean re-import, delete the project's predictions in Label Studio first.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import setup_label_studio_projects as s  # noqa: E402

RESULT_ZIP = s.ROOT / "data/bootstrap/qr4_predictions_result.zip"
PROJECT_TITLE = "GeoClean training"
# Label Studio pre-fills only predictions whose model_version equals the project's, so the
# Roboflow boxes and the bootstrap boxes must share one tag. Provenance is not lost: each
# task's data.source says whether its boxes came from Roboflow or the bootstrap model.
PREFILL_TAG = "prefill"
OLD_TAGS = {"roboflow-import"}


def load_predictions() -> dict[str, dict]:
    if not RESULT_ZIP.exists():
        sys.exit(f"{RESULT_ZIP} not found. Download it from the Colab notebook and save it there first.")
    with zipfile.ZipFile(RESULT_ZIP) as z:
        data = json.loads(z.read("qr4_predictions.json"))
    return {p["item_id"]: p for p in data["predictions"]}


def fetch_tasks(project_id: int) -> list[dict]:
    tasks, page = [], 1
    while True:
        batch = s.call("GET", f"/api/tasks/?project={project_id}&page={page}&page_size=200")
        results = batch.get("tasks", batch.get("results", batch if isinstance(batch, list) else []))
        if not results:
            break
        tasks.extend(results)
        if len(results) < 200:
            break
        page += 1
    return tasks


def to_result(boxes: list[dict]) -> list[dict]:
    return [
        {
            "id": f"bootstrap{i}", "from_name": "label", "to_name": "image", "type": "rectanglelabels",
            "value": {
                "x": b["x1"] * 100, "y": b["y1"] * 100,
                "width": (b["x2"] - b["x1"]) * 100, "height": (b["y2"] - b["y1"]) * 100,
                "rotation": 0, "rectanglelabels": [b["class"]],
            },
        }
        for i, b in enumerate(boxes)
    ]


def main() -> None:
    predictions = load_predictions()
    project = s.find_project(PROJECT_TITLE)
    if project is None:
        sys.exit(f'Project "{PROJECT_TITLE}" not found. Run setup_label_studio_projects.py first.')

    tasks = fetch_tasks(project["id"])
    by_item_id = {t["data"].get("item_id"): t["id"] for t in tasks}

    qr4_task_ids = {tid for iid, tid in by_item_id.items() if str(iid).startswith("qr4-")}

    # Retag existing Roboflow predictions, and refuse to double-import onto QR4Change tasks.
    existing = s.call("GET", f"/api/predictions/?project={project['id']}")
    existing = existing.get("results", existing) if isinstance(existing, dict) else existing
    existing = [p for p in existing if p.get("project") in (None, project["id"])]
    if any(p["task"] in qr4_task_ids for p in existing):
        sys.exit("QR4Change tasks already have predictions; delete them in Label Studio before re-importing.")
    retagged = 0
    for p in existing:
        if p.get("model_version") in OLD_TAGS:
            s.call("PATCH", f"/api/predictions/{p['id']}/", {"model_version": PREFILL_TAG})
            retagged += 1

    payload, unmatched, empty = [], 0, 0
    for item_id, pred in predictions.items():
        task_id = by_item_id.get(item_id)
        if task_id is None:
            unmatched += 1
            continue
        if not pred["boxes"]:
            empty += 1
            continue
        scores = [b["confidence"] for b in pred["boxes"]]
        payload.append({
            "task": task_id, "result": to_result(pred["boxes"]),
            "score": round(sum(scores) / len(scores), 3), "model_version": PREFILL_TAG,
        })

    if not payload:
        sys.exit("No predictions matched a task with at least one box; nothing imported.")

    result = s.call("POST", f"/api/projects/{project['id']}/import/predictions", payload)
    s.call("PATCH", f"/api/projects/{project['id']}/", {"show_collab_predictions": True, "model_version": PREFILL_TAG})
    print(f"Retagged {retagged} existing Roboflow predictions to '{PREFILL_TAG}'.")
    print(f"Imported bootstrap predictions for {len(payload)} QR4Change images ({result.get('created', '?')} created).")
    print(f"{empty} QR4Change images got no detection (still worth a look; the model may have missed a pile).")
    if unmatched:
        print(f"{unmatched} item_ids in the prediction file had no matching task (check the manifest is unchanged).")
    print(f"Project prefill tag set to '{PREFILL_TAG}': {s.BASE}/projects/{project['id']}/data")


if __name__ == "__main__":
    main()
