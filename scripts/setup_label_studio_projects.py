"""Create the GeoClean Label Studio projects, image storages and task imports.

Reads LABEL_STUDIO_TOKEN from .env: the Personal Access Token from Account & Settings
in Label Studio. The token is exchanged for a short-lived access token on every request
and is never printed. Safe to rerun: an existing project is reused, and tasks are
imported only into a project that has none.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8080"
CONFIG = (ROOT / "config/label-studio-config.xml").read_text(encoding="utf-8")
TASKS = ROOT / "data/labelling"

PROJECTS = [
    {
        "title": "GeoClean training",
        "storage": ROOT / "data",
        "task_files": ["tasks-qr4change.json", "tasks-overflow.json", "tasks-piles.json"],
        "prelabel": True,
    },
    {
        # Separate project so Pune diagnostic images never appear in training exports.
        "title": "GeoClean Pune diagnostic",
        "storage": ROOT / "reports/visual-review",
        "task_files": ["tasks-pune-diagnostic.json"],
        "prelabel": False,
    },
]


def read_token() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip() == "LABEL_STUDIO_TOKEN" and value.strip():
            return value.strip().strip("'\"")
    sys.exit("Add LABEL_STUDIO_TOKEN=<Personal Access Token> to .env first.")


TOKEN = read_token()
# Reuse one short-lived access token for a couple of minutes; refreshing before every
# request doubled the round trips and made bulk updates take over an hour.
ACCESS_REUSE_SECONDS = 120
_access = {"header": None, "at": 0.0}


def auth_header() -> str:
    # Personal Access Tokens are JWT refresh tokens; legacy tokens have no dots.
    if TOKEN.count(".") != 2:
        return f"Token {TOKEN}"
    if _access["header"] is None or time.monotonic() - _access["at"] > ACCESS_REUSE_SECONDS:
        access = call("POST", "/api/token/refresh/", {"refresh": TOKEN}, authorise=False)["access"]
        _access.update(header=f"Bearer {access}", at=time.monotonic())
    return _access["header"]


def call(method: str, path: str, body=None, authorise: bool = True):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if authorise:
        request.add_header("Authorization", auth_header())
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:500]
        if err.code in (401, 403):
            sys.exit(f"Label Studio refused {method} {path} (HTTP {err.code}). Check LABEL_STUDIO_TOKEN.")
        sys.exit(f"{method} {path} failed (HTTP {err.code}): {detail}")
    except urllib.error.URLError:
        sys.exit("Label Studio is not reachable at http://localhost:8080. Start it with scripts\\Start-LabelStudio.ps1.")


def find_project(title: str):
    listing = call("GET", "/api/projects/?page_size=100")
    projects = listing.get("results", listing) if isinstance(listing, dict) else listing
    return next((p for p in projects if p.get("title") == title), None)


def main() -> None:
    for spec in PROJECTS:
        project = find_project(spec["title"])
        if project is None:
            project = call("POST", "/api/projects/", {"title": spec["title"], "label_config": CONFIG})
            print(f"{spec['title']}: created project {project['id']}")
        else:
            print(f"{spec['title']}: using existing project {project['id']}")
        pid = project["id"]

        storages = call("GET", f"/api/storages/localfiles/?project={pid}")
        storage_path = str(spec["storage"])
        if not any(Path(s.get("path", "")) == spec["storage"] for s in storages):
            call("POST", "/api/storages/localfiles/", {
                "project": pid, "path": storage_path, "title": spec["storage"].name,
                "use_blob_urls": False, "regex_filter": "",
            })
            print(f"{spec['title']}: added Local files storage {storage_path}")

        if call("GET", f"/api/projects/{pid}/").get("task_number", 0) == 0:
            for name in spec["task_files"]:
                tasks = json.loads((TASKS / name).read_text(encoding="utf-8"))
                result = call("POST", f"/api/projects/{pid}/import", tasks)
                print(f"{spec['title']}: imported {name}: {result.get('task_count', '?')} tasks, "
                      f"{result.get('prediction_count', 0)} pre-filled predictions")
        else:
            print(f"{spec['title']}: already has tasks; import skipped")

        if spec["prelabel"]:
            call("PATCH", f"/api/projects/{pid}/", {"show_collab_predictions": True, "model_version": "roboflow-import"})
            print(f"{spec['title']}: prelabelling on with model version roboflow-import")
        print(f"{spec['title']}: {BASE}/projects/{pid}/data")


if __name__ == "__main__":
    main()
