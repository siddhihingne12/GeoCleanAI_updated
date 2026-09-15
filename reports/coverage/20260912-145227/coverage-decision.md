# GeoClean AI V2 - Pune peth screening round 1, coverage decision

Scan completed: 12 September 2026, 14:52 UTC. Decision and visual review recorded 12 September 2026.

## Decision

**Neither Pune candidate is approved.** Bhavani Peth - Nana Peth fails the freshness gate outright. The Kasba - Mangalwar - Raviwar belt passes the metadata gate but was then rejected on image content; see [the visual review](../../visual-review/pune-kasba-belt/review.md).

Continue down [the Pune search queue](../../../PUNE_SEARCH_PLAN.md) from entry 3. Existing PCMC results in `../20260912-142113/` remain historical evidence and are not Pune coverage.

## Results

| Check | Bhavani Peth - Nana Peth | Kasba - Mangalwar - Raviwar belt |
|---|---:|---:|
| Unique returned images | 589 | 1,058 |
| Images within the past 24 months | **0** | 659 (62%) |
| Recent images with sequence, heading and dimensions | 0 | 659 |
| Remaining after approximately 5 m spacing within sequences | 0 | 452 |
| Sequence IDs represented after spacing | 0 | 23 |
| **Distinct physical locations** (sequence centroids merged within 40 m) | 0 | **13** |
| Earliest capture | 2016-02-02 | 2016-02-02 |
| Latest capture | **2019-10-27** | 2026-08-04 |
| Perspective images | 589 | 1,004 |
| Spherical panoramas | 0 | 6 |
| Brown-model images | 0 | 48 |
| Images with camera parameters | 589 | 1,052 |
| Images with original heading and corrected position | 589 | 1,058 |
| Completed search cells | 30 of 30 | 36 of 36 |
| Metadata gate: ≥ 300 spaced recent images and ≥ 3 sequences | **FAIL** | PASS |
| Image-content gate: clear positives for both classes | not applicable | **FAIL** |

The recent cutoff was 2024-09-12 at the check's UTC time. Counts refer only to these search rectangles and API responses, not to all of Bhavani Peth, Nana Peth, Kasba Peth or Pune.

Bounding boxes use west longitude, south latitude, east longitude, north latitude:

- Bhavani Peth - Nana Peth: `73.864,18.506,73.874,18.518`
- Kasba - Mangalwar - Raviwar belt: `73.854,18.516,73.866,18.528`

The rectangles overlap slightly and their counts must never be summed without deduplication. Anchor landmarks and sources are in `candidate-config.json`.

## Bhavani Peth - Nana Peth: stale coverage

The area holds 589 images with complete metadata across 8 sequences, but every capture falls between February 2016 and October 2019. Not one frame lies inside the 24-month window, so the freshness requirement fails by the widest possible margin and no visual review was run.

The imagery is not worthless: it is perspective-only with camera parameters on all 589 frames, which makes it reasonable test material for the pixel-to-bearing and triangulation work. It cannot support a claim about current waste locations, which is the project's actual output.

## Kasba - Mangalwar - Raviwar belt: counts pass, content does not

452 spaced recent frames across 23 sequence IDs clears the numeric gate, and the newest capture is 4 August 2026, about five weeks before the check. The camera mix is also more favourable than the PCMC results: perspective-dominant with calibration parameters on 1,052 of 1,058 frames, against PCMC Area B's 1,117 panoramas, which removes most of the panorama-cropping work.

Visual review of all 43 sampled frames then found zero clear `roadside_dump` and zero clear `overflowing_bin`, one weak accumulation site, four uncertain scattered-litter observations, one useful difficult negative, and 10 frames unusable through camera aim, motion blur or pedestrian occlusion. The full record is in [the visual review](../../visual-review/pune-kasba-belt/review.md).

Two structural problems matter more than the absent positives, because they would have surfaced during week 2 rather than week 1:

1. **The recent frames are five unrelated capture styles**, not a corridor survey: a car dashcam, an upward-aimed facade sequence, a dusk side-window sequence with sill occlusion, a handheld walking market capture, and a low-aimed two-wheeler mount. The upward and dusk sequences alone are 291 of 659 recent frames that contribute little ground coverage.
2. **Sequence IDs are not independent routes.** 23 recent sequence IDs resolve to 13 distinct physical locations, four route-scale captures hold 94% of the recent frames, and three sequence IDs share one identical coordinate. The single weak accumulation site is reachable through five sequence IDs at once.

## Method and reproducibility

The checker reads candidates from `config/pune-candidates.json`, divides each rectangle into 0.002-degree cells, requests explicit metadata fields, follows pagination, deduplicates by image ID and clips results to the candidate boundary. A ten-page cap per cell marks results incomplete if reached; it was not reached. All 66 cells completed with no failures.

Spacing retains the first eligible frame in each sequence, then frames at least five metres from the last retained camera position, ordered by capture timestamp and ID, using the haversine formula on original camera coordinates.

Run from the project root:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Measure-MapillaryCoverage.ps1 -SelfTest
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Measure-MapillaryCoverage.ps1 -CandidateConfig config/pune-candidates.json
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Get-MapillaryReviewSample.ps1 `
  -MetadataFile 'reports/coverage/20260912-145227/pune_kasba_mangalwar_raviwar-images.json' `
  -OutputFolder 'reports/visual-review/pune-kasba-belt' -PerSequence 3
```

The scripts read the token locally from `.env`. Reports contain image metadata, not authorization headers or pagination URLs.

Evidence in this directory: `summary.json`, `candidate-config.json`, `pune_bhavani_nana-images.json`, `pune_kasba_mangalwar_raviwar-images.json`.

## Changes made after this run

1. `Measure-MapillaryCoverage.ps1` now reports **distinct physical locations** by merging sequence centroids within 40 m, and gates on that figure rather than on sequence-ID count alone. Sequence-ID count was the misleading number in this round.
2. `Get-MapillaryReviewSample.ps1` now filters samples to the freshness window before sampling, so review effort is never spent on frames already excluded by the coverage gate, and it no longer emits duplicate rows for sequences shorter than the requested sample size.

## Issues carried forward

1. **Heading conventions still unvalidated.** Original and corrected headings must be checked against visible landmarks with the matching projection before any triangulation. Not addressed by this round.
2. **Gate on distinct physical sites, not sequence IDs**, for every remaining candidate. Also confirm route overlap before allocating evaluation groups.
3. **Mixed capture styles are the norm in crowdsourced coverage**, not an accident of this belt. Expect to screen candidates for camera-aim consistency, and expect a usable corridor to rest on one or two coherent captures rather than a sequence count.
4. **Positive examples, not frame counts, are the binding constraint.** Two candidates have now passed metadata and failed content. If entries 3-10 repeat this, the data constraint itself is the finding and needs a scope decision; do not relax the class definitions or the freshness window to manufacture a pass.
