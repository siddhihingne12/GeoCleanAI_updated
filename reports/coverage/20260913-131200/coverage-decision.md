# Pune Aundh screening, round 8b

Checked 13 September 2026. **Metadata passes; image review finds one roadside-dump site and no overflowing bin. Corridor not approved.**

| Check | Result |
|---|---:|
| Unique image records | 3,220 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 739 |
| Recent frames after approximately 5 m spacing | 474 |
| Recent sequences after spacing | 14 |
| Sequence-centroid clusters | 9 |
| Oldest / newest capture in the rectangle | 2019-01-24 / 2026-05-19 |
| Completed search cells | 42/42 |
| Distinct downloaded images individually reviewed | 60 |
| Confirmed roadside-dump sites / positive frames | 1 / 8 |
| Confirmed overflowing-bin samples | 0 |

All search cells completed without recorded failures or pagination caps. Across all dates the rectangle holds 2,612 perspective, 394 spherical and 214 Brown-model images; 2,826 carry camera parameters and 3,120 carry corrected positions. Capture years: 2,481 frames from 2019, 702 from 2025 and 37 from 2026. The nine centroid clusters approximate route separation, but the recent frames come from only eight capture days, and several clusters repeat the same bridge and boulevard.

## Location and bounds

Bounds in west/south/east/north order: `73.804,18.557,73.817,18.569`. This exploratory public-road rectangle covers Parihar Chowk, Bremen Chowk and the Aundh Gaon market approaches, reaching the river-bridge approach at its north edge. It is not a municipal boundary. Private and river interiors are outside target scope.

Location anchors: [Parihar Chowk](https://mapcarta.com/N2668919264) at 18.56058, 73.80922; [Bremen Chowk](https://mapcarta.com/N4616977052) at 18.56055, 73.81489; and [Aundh Vitthal Mandir near Aundh Market](https://mapcarta.com/W359687254) at 18.56714, 73.81106. These support search placement only.

## Content decision

The 40-image initial sample contains one confirmed roadside dump, one weak accumulation below threshold, 25 no-clear-target frames, six limited-visibility frames, four hard-negative candidates, two uncertain scattered-litter frames and one indoor frame with unusable camera aim.

The dump lies on the verge along the river-bridge approach railing, with the camera near 73.81158, 18.56760. Nine consecutive frames confirm it in eight of them, all at one physical site. Nearest frames from four other recent passes neither confirm nor rule out persistence. A tarp-covered bundle elsewhere was resolved as stored material.

One site cannot support the planned annotation set of 100-150 dump-positive images from at least 15 distinct mapped sites. The complete absence of overflowing bins also leaves the second class unsupported. The site and its frames are worth keeping as the first genuine Pune positive, useful for a geometry trial or as seed labelling material.

See the [visual review](../../visual-review/pune-aundh/review.md) for per-image evidence and galleries.

## Reproduction

`Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-131200/candidate-config.json`. Initial sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-131200/pune_aundh-images.json -OutputFolder reports/visual-review/pune-aundh -PerSequence 3`. The bridge check used `-SequenceId BEohfHsAZiWFlVXwp7Gz4N -FocusImageId 765068579834233 -PerSequence 9`, and the tarp check used `-SequenceId Le2TjoQ1ms3uyCwfYOKGlR -FocusImageId 1387747582372489 -PerSequence 9`. Persistence frames used `-PerSequence 1` with each sequence's closest frame as `-FocusImageId`. Freshness advances on rerun; the summary preserves this run's cutoff.
