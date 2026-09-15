# Bootstrap detector (labelling aid)

Trained 13-14 September 2026 on Colab with `notebooks/geoclean_bootstrap_train.ipynb`. **This is not the project detector.** It exists only to pre-draw boxes on the 707 QR4Change photos, which had none, so labelling in Label Studio means correcting boxes instead of drawing all of them.

## Training data

`scripts/build_bootstrap_dataset.py` takes the already-boxed Roboflow images that the labelling manifest queued. Stock photos and pre-augmented copies are removed. It keeps only boxes of the matching source class, remapped to the two project classes:

| Split | Images | roadside_dump boxes | overflowing_bin boxes |
|---|---:|---:|---:|
| train | 872 | 265 | 1,227 |
| val | 147 | 57 | 173 |

Split groups stay whole (821 train groups, 145 val groups; seed 20260913), so near-duplicate frames do not cross splits.

**Class imbalance:** the training set holds about 4.6 overflowing_bin boxes for every roadside_dump box.

**The labels are unreviewed Roboflow labels.** The overflow set's "Trash over flow" class is broader than the project's `overflowing_bin` definition ([dataset review](../dataset-review.md)).

## Result

YOLOv8n, 640 px, batch 16, 60 epochs on a T4. The best epoch was the last one (60):

| mAP50 | mAP50-95 | Precision | Recall |
|---:|---:|---:|---:|
| 0.941 | 0.680 | 0.895 | 0.881 |

These are validation figures on held-out groups from the same two Roboflow sources, scored against their own unreviewed labels. They show the model learned those labels. They do **not** measure performance on Pune scenes or against the project class definitions, and they must not be reported as detector results.

Curves, confusion matrices, `results.csv` and `bootstrap_best.pt` are in `data/bootstrap/qr4_predictions_result.zip`.

## Predictions on QR4Change

Images were resized to a 1,280 px long edge before upload. Box coordinates are normalised, so they apply unchanged to the full-size originals. The confidence threshold was 0.25.

- 496 of 707 images received at least one box; 211 received none.
- 651 boxes: 560 roadside_dump, 91 overflowing_bin.
- Median box confidence was 0.45; 277 boxes scored 0.5 or higher.

Earlier segment review estimated about 31 of 58 QR4Change capture segments show a clear dump, so many of these boxes will be false positives on sparse litter, soil or garden waste. Some real piles will also be missed. Manual review was later skipped: the 194 images whose boxes all scored 0.5 or higher were accepted as labels without checking ([automatic labelling](README.md#automatic-labelling-14-september-2026)).

## Label Studio prefill

`scripts/import_qr4_predictions.py` loads these boxes onto the QR4Change tasks in "GeoClean training". Label Studio pre-fills only predictions whose model version matches the project setting. The Roboflow and bootstrap boxes therefore share the tag `prefill`, and each task's `source` field records which set its boxes came from.
