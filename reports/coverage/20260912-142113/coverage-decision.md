# GeoClean AI V2 - initial Mapillary coverage decision

Checked: 12 September 2026, 14:21 UTC.

**Superseded location preference:** the user has moved corridor discovery to [the Pune shortlist](../../../PUNE_SEARCH_PLAN.md). Area A/B metadata and the subsequent Area B review remain historical PCMC evidence. Their counts are not Pune coverage results.

## Decision

Both preliminary search areas pass the metadata gate. Prefer **candidate B for the first visual inspection**, because it has more recent images remaining after spacing. This is a provisional choice, not a final corridor or training-dataset approval.

**Visual review update, 12 September 2026:** all 27 sampled candidate B images were inspected. No clear dump or overflowing bin was identified at the review resolution. Full annotation is on hold; inspect candidate A next. See [the visual review](../../visual-review/candidate-b/review.md). The metadata counts below remain valid and must not be interpreted as confirmed waste-training examples.

No self-capture is required by the present metadata results. Respect the user's preference to avoid field collection. If visual inspection reveals insufficient examples, search additional existing PCMC coverage before discussing any change of approach.

## Results

| Check | Candidate A (northern rectangle) | Candidate B (southern rectangle) |
|---|---:|---:|
| Unique returned images | 907 | 1,167 |
| Images within the past 24 months | 907 (100%) | 1,167 (100%) |
| Recent images with sequence, heading and dimensions | 907 | 1,167 |
| Remaining after approximately 5 m spacing within sequences | 587 | 736 |
| Sequences represented after spacing | 9 | 9 |
| Earliest capture | 2025-02-20 | 2025-02-20 |
| Latest capture | 2026-01-19 | 2026-01-19 |
| Spherical panoramas, before spacing | 712 | 1,117 |
| Perspective images, before spacing | 195 | 50 |
| Perspective images with camera parameters | 195 | 50 |
| Images with original heading and corrected position | 907 | 1,167 |
| Completed search cells | 8 of 8 | 8 of 8 |
| Metadata gate: at least 300 spaced recent images and 3 sequences | PASS | PASS |

The recent cutoff was 2024-09-12 at the check's UTC time. Counts refer only to these search rectangles and API responses, not all of Nigdi or PCMC. They do not establish 300 visually usable images, sufficient positive examples, distinct waste sites, or independent evaluation groups.

Bounding boxes use west longitude, south latitude, east longitude, north latitude:

- Candidate A: `73.766,18.650,73.774,18.654`.
- Candidate B: `73.766,18.646,73.774,18.650`.

These are exploratory rectangles around the successful connection-test location. Final road names, boundaries and inspected road length remain to be established from the map and images.

## Method and reproducibility

The checker divides each rectangle into eight 0.002-degree cells, requests explicit metadata fields, follows pagination, removes duplicate image IDs and clips results to the candidate boundary. A ten-page limit per cell marks results incomplete if reached; it was not reached in this run. Sixteen successful pages covered both areas, with no failed cells.

Spacing retains the first eligible image in each sequence and then images at least five metres from the last retained camera position, ordered by capture timestamp and ID. Distances use the haversine formula on original camera coordinates. This reduces nearby frames but does not eliminate repeated visits to the same site or establish independent viewpoints.

Run from the project root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Measure-MapillaryCoverage.ps1 -SelfTest
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Measure-MapillaryCoverage.ps1
```

The script reads the token locally from `.env`. Reports contain image metadata, not authorization headers or pagination URLs. Each scan creates a timestamped result folder.

Tests passed for a known geographic distance, five-metre frame selection and separation between sequences. Live queries completed for all sixteen cells.

Evidence: `summary.json`, `candidate_a-images.json`, and `candidate_b-images.json` in this directory. The summary contains Mapillary image links and capture-year counts.

## Issues to resolve before training

1. **Image content remains uninspected.** Download a modest sample from every candidate B sequence, covering both camera types and capture dates. Review blur, obstructions, viewing direction and visible examples of both waste classes. Expand sampling if necessary before approving annotation.
2. **Panoramas dominate.** Candidate B contains 1,117 spherical images and 50 perspective images before spacing. Establish a consistent panorama-to-perspective crop workflow for annotation and detection, with transformations retained for mapping detections back to the original panorama and viewer.
3. **Heading conventions need validation.** Original and corrected headings differ by more than 30 degrees for 456 candidate A images and 517 candidate B images. Different orientation conventions or reconstruction corrections may explain this; the discrepancy alone does not prove either field is wrong. Do not assume they are interchangeable. Validate pixel-to-bearing conversion against visible landmarks using the matching projection and orientation metadata before triangulation.
4. **Spherical images have no perspective camera parameters in this response.** Do not reject them solely for that absence. Use spherical projection; use calibration parameters for perspective images. Fetch additional rotation/orientation metadata during the geometry trial. See [Mapillary's metadata documentation](https://mapillary.github.io/mapillary-python-sdk/docs/mapillary.config.api/mapillary.config.api.entities/).
5. **Nine sequences do not prove a leakage-free split.** Inspect route overlap and repeated physical sites before allocating training, validation and test groups. Never use A and B directly as independent splits without checking shared routes and sites.
6. **Locations will be evaluated remotely.** Report approximate alignment and reference uncertainty. No field-verified accuracy claim is supported.

Next deliverable: a sample-image review and a final corridor decision. Do not start full annotation or training until that review establishes sufficient usable waste examples.
