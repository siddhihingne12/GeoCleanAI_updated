# Pune Poona Hospital bridge screening, round 3

Checked 13 September 2026. **Metadata passes; the corridor is not approved after initial content screening.**

| Check | Result |
|---|---:|
| Unique image records | 1,934 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 1,012 |
| Recent images after approximately 5 m spacing | 805 |
| Recent sequences after spacing | 15 |
| Sequence-centroid clusters | 12 |
| Oldest / newest capture | 2015-06-26 / 2026-03-05 |
| Completed search cells | 16/16 |
| Downloaded and reviewed samples | 43 |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

The search completed without recorded cell failures. Counts describe the saved rectangle, not all nearby streets. The full metadata population contains 1,914 perspective and 20 brown-camera records; all 43 recent review samples are perspective images. Centroid clusters approximate route separation and do not establish physical waste sites or independent evaluation groups.

## Location and bounds

The exploratory rectangle is west/south/east/north `73.838,18.508,73.846,18.516`. The named two-wheeler bridge is identified as Yashwantrao Chavan Bridge by the [Punekar News location description](https://www.punekarnews.in/pune-entry-of-vehicles-restricted-on-two-wheeler-bridge-connecting-karve-road-to-poona-hospital/). This source is used for identity, not current traffic restrictions or cleanliness.

Anchors are the [hospital-side bridge photograph geotag](https://commons.wikimedia.org/wiki/File:View_of_Yashwantrao_Chavan_Bridge_from_one_end_near_Poona_Hospital.jpg) at 18.511163, 73.842035 and [Poona Hospital coordinates](https://www.latlong.net/poi/poona-hospital-and-research-centre-366707) at 18.5106347, 73.8419468. The rectangle includes neighbouring road approaches and is not an approved study corridor. The supplied cleanliness claim remains unverified.

## Content and next step

All 43 samples have individual notes: 18 no-clear-target, 12 limited-visibility, four potential negatives, one below-threshold accumulation and eight unusable frames. No confirmed positive of either class was found. This result applies to the sample, not every available frame. See the [visual review](../../visual-review/pune-poona-hospital-bridge/review.md) and [gallery](../../visual-review/pune-poona-hospital-bridge/index.html).

The newest imagery and high frame count do not establish the class balance needed for training. Keep the evidence, leave annotation on hold and move to queue entry 5: selected Hadapsar market edges and lanes.

## Reproduction

Use `candidate-config.json` in this folder with `Measure-MapillaryCoverage.ps1 -CandidateConfig`. Review sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-073542/pune_poona_hospital_bridge-images.json -OutputFolder reports/visual-review/pune-poona-hospital-bridge -PerSequence 3`. Run scripts through `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` if local execution policy requires it. Freshness advances on rerun; the saved summary preserves this run's cutoff. Source metadata, configuration, manifest and notes are retained.
