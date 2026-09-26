# Baseline v1 — rejected

Status: **REJECTED. Do not install in `models/` or use in the demo.**

Preserved copy: `artifacts/runs/baseline-v1/` (read-only files, `CHECKSUMS.txt`, `evaluation-record.json`). The original download `artifacts/colab/geocleanai-model-and-results.zip` is unchanged.

## What was trained

- Pretrained YOLO26n, one class `litter`, 640px input, batch 8, up to 50 epochs, patience 10, seed 42 (`training/train.py`).
- Data: TACO split `533d3e4a…` — 999 train / 324 val / 177 test images, grouped by TACO upload batch (14 groups).
- Epochs actually completed: **unconfirmed**. `results.csv` and `args.yaml` stayed in the Colab Drive run folder.
- Versions recorded by the run: ultralytics 8.4.163, torch 2.11.0+cu128, onnxruntime 1.30.0. The requirements pin ultralytics 8.4.155; the cause of the difference is not yet known.

## Results

| Set | Operating point | Precision | Recall | Notes |
|---|---|---|---|---|
| TACO test (177) | Ultralytics val default | 70.6% | 36.2% | mAP50 43.1%, mAP50-95 29.9%. Not at 0.35; not comparable with Pune. |
| Pune test v1 (48 views, 54 regions) | conf 0.35, IoU 0.50 | 0% (0/21) | 0% (0/54) | TP 0, FP 21, FN 54 |

`manifest.json` and `metrics.json` in the bundle say `"pune_evaluation": "Not yet run"`. That text was written before the Pune evaluation ran and was never updated; `evaluation-record.json` holds the actual result.

## What the numbers show

- Only 21 boxes were predicted across 48 views, so recall could not have exceeded 39% even if all were correct.
- 13 of the 21 false alarms are in one panorama (207405678297886); 17 are in views with no labelled litter.
- Only four views contain both a false alarm and a missed region, so near-misses (box placement or cluster labelling) can account for at most 4 matches (recall ≤ 7%).
- Pune test views are 640×640, so letterbox resizing and padding are identity operations for this test set.
- The 54 test labels match the reviewer's saved boxes; TACO images carry no EXIF rotation.
- ONNX matched PyTorch on 47 of 48 images. The one failure (IoU 0.9841 < 0.99) is unexplained and does not by itself indicate corruption.

Open questions and the diagnosis plan are in the project plan (Phase 1). The Pune per-image results have been inspected; they are used for diagnosis only, never for tuning or model selection.

## Diagnosis results (Colab notebook A, 26 September 2026)

Files: `artifacts/runs/diagnosis-baseline-v1/`. Gate 1 passed: checksums, ONNX-vs-manifest, training split and label pairing all match; regression tests passed; the official 0/21/54 was reproduced; PIL-RGB and OpenCV-BGR inputs gave the same boxes.

- **Not undertrained.** 49 epochs ran; best at epoch 39; stopped by early stopping. Validation mAP and recall had plateaued. More epochs would not help.
- **Small litter is the main technical limit, even on TACO.** TACO test at the fixed 0.35 threshold: precision 73%, recall 35%. Recall by size at 640px: under 8 px 0.7%, 8–16 px 9%, 16–32 px 33%, 32 px and over 68%. 61% of Pune regions are under 16 px. If size were the only problem, TACO's size-by-size recall would predict about 21% Pune recall; the actual 0% shows an additional domain gap.
- **Domain gap.** Of the 9 Pune regions 32 px or larger, 8 had no prediction nearby even at confidence 0.05.
- **Misses are not box-placement or cluster problems.** At confidence 0.05: 50 of 54 regions had no prediction nearby, 2 were near-misses, 2 matched (diagnostic only).
- **False alarms are look-alikes, not missed labels.** In panorama 207405678297886 the model fired on the national flag and on people. No evidence of Pune label errors; no v1.1 correction needed.
- **ONNX export is sound.** Box counts always equal and confidences agree to within 0.000002. Every box mismatch above 1 px is a box touching the image border (PyTorch clips to the image; raw ONNX output does not; the app clips when decoding). Remaining failures are 0.2–0.7 px differences on small boxes. Decision (26 September 2026): from now on both boxes are clipped to the image before comparison, and a pair passes at IoU ≥ 0.99 or with every corner within 1 px; the old strict result is still recorded.
- **Versions.** The diagnosis ran on the pinned Ultralytics 8.4.155 with auto-install disabled. The original training recorded 8.4.163; the cause of that drift is still unknown.
- **Resolution helps on paper.** Rendering the same Pune views at 1024 px cuts regions under 8 px from 30% to 7% and under 16 px from 61% to 41%.
