# Training data quality (TACO → litter-v2)

Repeatable checks for the training data. The Pune test set is never edited here; see "Pune test corrections" below.

## 1. Automated checks — run on all 1,500 TACO images

`python training/quality_check.py` → `data/litter-review/` (refuses to overwrite an earlier review).

Result, 26 September 2026:

| Check | Result |
|---|---|
| Image opens, size matches annotation, RGB | all 1,500 pass |
| EXIF orientation | all 1 (rotation was applied at download) |
| Boxes outside the image or empty | 7 boxes in 7 images — queued for review |
| Near-duplicate boxes in one image (IoU > 0.9) | 1 pair — queued |
| Boxes under 2 px | none |
| Blurriest 5% of images (Laplacian variance < 99.7) | 75 — queued as *possibly difficult*; blur alone is **not** a reason to remove |
| Related photos across splits (256-bit hash, ≤ 24 bits apart) | **0 pairs** (the earlier 12-bit audit found one exact duplicate, already merged) |
| Source URL present | all 1,500 |
| Licence resolved | **715 unresolved** ("Check original image source") — must be resolved before publishing any images |

Queue: 82 flagged images + a seeded stratified sample (split × box size), **232 images** in `review-queue.csv`, each with a picture in `queue/`.

## 2. Manual review — fill in `data/litter-review/review-queue.csv`

Open each `queue/<image_id>.jpg` (magenta boxes, numbered) and fill in four columns:

| Column | Values | Effect |
|---|---|---|
| `status` | `usable` / `difficult` / `unusable` | Only **unusable** leaves training. Difficult images stay. Val and test are never reduced. |
| `annotation_complete` | `yes` / `no` | Only `yes` images may supply litter-free (negative) tiles. |
| `tags` | `small clutter shadows leaves road_markings low_light glare occluded cluster` | Coverage counts per split. |
| `notes` | free text | **Required** for `unusable`. |

Definitions:

- **Litter:** discarded man-made waste — packaging, bottles, cans, bags, cups, paper, cigarette butts, wrappers, fragments.
- **Compact cluster:** touching pieces that cannot be told apart → one tight box. Pieces that can be told apart → separate boxes (same rule as the Pune labels).
- **Not litter (confusers):** leaves, stones, soil clods, shadows, road markings, drain covers, bins, vehicle parts, signage, construction material, animal waste.
- **Unusable:** wrong or misaligned labels, corrupt image, or not a litter scene.
- **Difficult but valid:** small, occluded, cluttered, shadowed or blurred litter with correct labels.

Checklist per image:

- [ ] Correct orientation and enough detail to recognise the litter
- [ ] Every box tight and complete; no box on a confuser
- [ ] No visible litter left unlabelled (→ `annotation_complete`)
- [ ] Cluster rule followed
- [ ] Tags recorded

## 3. Street-like training tiles — `training/build_derivatives.py`

Why: Pune litter is small and soft because it is far from a 360° camera; TACO photos are sharp close-ups covering a metre or two of ground.

- Photos are **downscaled only** (never enlarged) so litter has the size of a 5–30 cm item at 2–20 m, at the detector's pixels-per-degree (6.4 for 640px views, 10.2 for 1024px views). These sizes come from camera geometry, **not** from Pune labels.
- A photo shrunk that far is smaller than a 640px tile, so each tile is a **collage of several shrunk photos from the same split** (each at least 128 px on its long side, so some ground stays around the litter). Photos are packed into the largest free space and cropped to fit; none repeats within a tile. Collage seams are artificial; this is a recorded limitation.
- Every TACO photo contains litter, so a pure collage is far denser than a street. Half of the collage areas (`--clean-share 0.5`) are therefore filled with **verified clean ground**: windows at least 16 px away from every box, taken only from photos marked `annotation_complete = yes`. Without review marks there is no clean ground to use.
- Labels under 3 px are dropped: below that, a single-pixel boundary error already puts IoU under 0.5, so the label cannot be scored.

Pilot measurements (26 September 2026, before any review; scratch builds, not training data):

| Build | Grey padding | Litter labels per tile | Labels under 8 px |
|---|---|---|---|
| First pilot (row packing), all 1,998 train tiles | 31% | 25 | 40% |
| Free-space packing, 150-tile sample | 12% | 55 | 33% |
| Free-space packing + clean fill, 150-tile sample (sample photos *treated* as complete for measurement only) | 2% | 14 | 32% |

The more photos the review marks `annotation_complete = yes`, the closer tiles get to street-like density.
- Mild blur (σ ≤ 1 px), noise, brightness/contrast change, occasional shadow band and JPEG quality 60–92. **None of this adds detail**; it shows the model what lost detail looks like.
- A box cut by a crop keeps its label only if ≥ 60% stays visible; otherwise its visible part is painted grey, so no half-labelled litter remains.
- Every tile uses photos from one split; the builder refuses to finish if any photo or capture group appears in two splits. `derivatives.json` records each tile's parents, scales, positions and degradation settings.
- Negative tiles only from `annotation_complete = yes` photos, at most ~10% of training images.
- Validation becomes the **street-like proxy** built only from val-split photos. Original TACO val is still reported separately.

Build after the review is filled in:

```
python training/build_derivatives.py --output data/litter-v2 --profile r640
python training/build_derivatives.py --output data/litter-v2-r1024 --profile r1024   # only if E3 is justified
```

## 4. Pune test corrections (only for confirmed errors)

The locked `data/pune-test-v1/` is never edited. If a genuine label error is confirmed (for example, while checking the 13 false alarms in panorama 207405678297886):

1. Re-check the view at original resolution in the review tool.
2. Create `data/pune-test-v1.1/` with `corrections.md` listing view, old box, new box, reason, reviewer and date. Correct in **both directions**: add missed litter as well as remove wrong boxes.
3. Report every model, including the baseline, on both v1 and v1.1, and disclose that model outputs had been seen before the correction.

## Storage note

The raw TACO photos were moved to `E:\GeoCleanAI-archive\TACO` (hash-verified; see `data/TACO/MOVED.txt`). `data/litter` keeps byte-identical copies used for training. Pass `--images E:\GeoCleanAI-archive\TACO` to `training/quality_check.py` or `training/audit_taco_groups.py` if they are re-run.
