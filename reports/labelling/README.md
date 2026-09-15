# Labelling workflow

Labelling uses Label Studio locally, approved on 13 September 2026 in place of CVAT: CVAT needs Docker, which is not installed, and this machine has 7.9 GB RAM. Label Studio is installed in `.venv` and keeps its database in `data/label-studio`, which is excluded from version control.

## What is in the queue

`scripts/build_label_manifest.py` writes [manifest.csv](manifest.csv), one row per candidate image with source, licence, split group, status, suggested class and exclusion reason. [summary.json](summary.json) has the counts. Import files are in `data/labelling/`:

| File | Tasks | Suggested class | Pre-filled boxes | Split groups |
|---|---:|---|---|---:|
| `tasks-qr4change.json` | 707 | roadside_dump (IMG 6-20: overflowing_bin) | bootstrap-detector boxes on 496 images, added after import ([details](bootstrap-detector.md)); 211 have none | 66 |
| `tasks-overflow.json` | 766 | overflowing_bin | Roboflow "Trash over flow" boxes, to be corrected | 694 |
| `tasks-piles.json` | 285 | roadside_dump | Roboflow pile boxes, to be corrected | 272 |
| `tasks-pune-diagnostic.json` | 33 | 8 Aundh dump frames, 25 hard negatives | none | 17 Mapillary sequences |

Each file lists the first image of every split group before any second image, so stopping early still covers the most distinct scenes. **You do not need to finish every task.** Aim for about 300-400 kept images per class, spread across groups, plus the hard negatives you mark along the way.

## One-time setup

**Automated route:** start the server and create your account (step 1). Then copy your Personal Access Token from *Account & Settings* into `.env` as `LABEL_STUDIO_TOKEN=...` and run `.venv\Scripts\python.exe scripts\setup_label_studio_projects.py`. It performs steps 2-6 and is safe to rerun. The manual steps below do the same thing.

1. Start the server: `powershell -ExecutionPolicy Bypass -File scripts\Start-LabelStudio.ps1`, then open http://localhost:8080 and create a local account. It stays on this computer.
2. Create a project named **GeoClean training**. Under *Settings → Labeling Interface → Code*, paste the contents of `config/label-studio-config.xml`.
3. Under *Settings → Cloud Storage → Add Source Storage*, choose **Local files** and set the absolute path to `C:\Users\VINEET\Documents\GeoCleanAI-main\data`. Save it without syncing. Label Studio refuses to serve local images unless a storage entry covers their folder.
4. Under *Settings → Annotation*, turn on prelabelling with model version `prefill` so the imported boxes appear as editable starting boxes. Roboflow boxes were first imported as `roboflow-import`; `scripts/import_qr4_predictions.py` retags them to `prefill` when it adds the bootstrap-detector boxes, because Label Studio pre-fills only one model version per project.
5. Import `tasks-qr4change.json`, `tasks-overflow.json` and `tasks-piles.json`.
6. Create a second project, **GeoClean Pune diagnostic**, with the same labelling config and a Local files storage pointing at `C:\Users\VINEET\Documents\GeoCleanAI-main\reports\visual-review`. Import `tasks-pune-diagnostic.json` there. Keeping Pune images in their own project stops them leaking into training exports.

If images show as broken, the storage path in step 3 or 6 is the usual cause.

## Rules for each image

- **roadside_dump**: a concentrated pile of discarded mixed or household waste on a roadside, verge or open plot. One box per pile.
- **overflowing_bin**: one box around the bin or container *together with* the waste spilling out of it or heaped around it.
- **Not targets**: scattered litter, construction rubble or soil, garden waste, stored or sale goods, and bins that are full but not spilling. Delete pre-filled boxes on these.
- Pick exactly one decision per image:
  - `keep`: at least one correct box.
  - `hard_negative`: no target, but something that looks like one (rubble, sacks, a full non-spilling bin). No boxes.
  - `reject_not_target`: irrelevant image.
  - `reject_quality`: blur, occlusion or an unreadable scene.

## Automatic labelling (14 September 2026)

Manual review was skipped for "GeoClean training". `scripts/auto_label.py` accepted the pre-filled boxes as `keep` annotations **without a person checking them**:

| Source | Annotated | Left unannotated |
|---|---:|---|
| Roboflow overflow | 766 | none |
| Roboflow piles | 285 | none |
| QR4Change | 194 (every bootstrap box scored at least 0.5) | 302 with a weaker box, 211 with no box |

An image with any weak box is left out entirely rather than having that box removed: a real pile without a box would teach the detector that piles are background. Images with no boxes are not marked `hard_negative`, because the model may have missed a pile. The Pune diagnostic project was not touched.

Each annotated task has `meta.label_origin = "auto-v1"`. Rerunning the script skips tasks that already have an annotation. **Metrics computed on these labels, including validation and test, score the model against unreviewed labels.** They must not be reported as reviewed detector results.

## Building the YOLO dataset

Run `.venv\Scripts\python.exe scripts\export_yolo_dataset.py` with Label Studio running. It reads the project's JSON export directly and writes `data/dataset/` with a 70/15/15 train, validation and test split by split group. `keep` images get their boxes, `hard_negative` images get empty label files, and rejected images are left out. `data/dataset/provenance.csv` records each image's split, decision and label origin (`auto-v1`, or `human` for tasks without that tag). The folder is rebuilt on every run, so rerun it after any correction in Label Studio.

Images with a long edge over 1,280 px (the QR4Change phone photos) are saved at 1,280 px. Labels are normalised, so they are unchanged, and training runs at 640 px anyway. The script finishes by writing `data/zips/geoclean_dataset.zip` for upload to `notebooks/geoclean_train.ipynb` on Colab.
