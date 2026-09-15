# Pune Pashan screening, round 8a

Checked 13 September 2026. **Metadata gate fails: one recent sequence at one location. Rejected.**

| Check | Result |
|---|---:|
| Unique image records | 2,442 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 51 |
| Recent frames after approximately 5 m spacing | 51 |
| Recent sequences after spacing | 1 |
| Sequence-centroid clusters | 1 |
| Oldest / newest capture in the rectangle | 2017-08-29 / 2026-01-12 |
| Completed search cells | 54/54 |
| Distinct downloaded images individually reviewed | 3 (supplementary) |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

All search cells completed without recorded failures or pagination caps. Every returned image is perspective imagery with camera parameters, compass and corrected position. Most imagery is older: 517 frames from 2019, 434 from 2020, 46 from 2022 and 1,317 from 2023, all before the cutoff. The gate needs at least 300 spaced recent frames across at least three distinct sites; Pashan has 51 frames at one site.

## Location and bounds

Bounds in west/south/east/north order: `73.780,18.533,73.797,18.545`. This exploratory rectangle covers Pashan village, Sutarwadi Road and the public-road approaches north and east of Pashan Lake. It is not a neighbourhood boundary.

Location anchors: [Pashan Lake Park on Sutarwadi Road](https://mapcarta.com/W395898751) at 18.53648, 73.78861, and the [Pashan Lake map-board photograph position](https://commons.wikimedia.org/wiki/File:Pashan_Lake_Map.jpg) at 18.536218, 73.781820. These support search placement only.

## Content note

Because the lone recent sequence was small, three distributed frames were checked anyway. All three are windscreen dashcam views of the divided highway at the rectangle's west edge, with the dashboard covering about a third of each frame. One shows no target and two show sparse litter below the dump threshold. See the [supplementary visual review](../../visual-review/pune-pashan/review.md).

## Reproduction

`Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-131135/candidate-config.json`; sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-131135/pune_pashan-images.json -OutputFolder reports/visual-review/pune-pashan -PerSequence 3`. Freshness advances on rerun; the summary preserves this run's cutoff.
