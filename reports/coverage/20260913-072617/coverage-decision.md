# Pune SRA-lead screening, round 2

Checked 13 September 2026 at 07:26 UTC. **Neither candidate is approved for training.** Dhankawadi fails freshness; Dandekar Bridge passes metadata but its initial visual sample does not establish positive examples.

| Check | Shankar Maharaj Vasahat / Dhankawadi | Dandekar Bridge vicinity |
|---|---:|---:|
| Unique image records returned | 139 | 1,221 |
| Recent images, cutoff 2024-09-13 | 0 | 465 |
| Recent metadata-eligible images | 0 | 465 |
| Images after approximately 5 m spacing | 0 | 412 |
| Recent sequence IDs after spacing | 0 | 5 |
| Sequence-centroid clusters within 40 m | 0 | 4 |
| Oldest capture | 2017-11-19 | 2018-11-24 |
| Newest capture | 2018-02-11 | 2026-01-19 |
| Completed search cells | 16/16 | 16/16 |
| Metadata gate | FAIL | PASS |
| Downloaded and reviewed samples | 0 | 15 |
| Confirmed dump / overflowing-bin samples | Not reviewed | 0 / 0 |

All 32 cells completed without recorded failures or pagination caps. Counts are restricted to the saved rectangles, not entire neighbourhoods. All returned images have perspective camera metadata. Route-centroid clusters are a screening heuristic, not confirmed physical waste sites or a validated data split.

## Location resolution and scope

- Dhankawadi bounds (west, south, east, north): `73.852,18.468,73.860,18.476`. The [mapped Shankar Maharaj Vasahat neighbourhood](https://mapcarta.com/N1831917530) is at 18.47112, 73.85562. [Shankar Maharaj Math on Pune-Satara Road](https://in.near-place.com/shankar-maharaj-math-beside-karnataka-bank-pune-satara-road-dhankawadi-pune) provides an eastern road anchor at 18.4707034, 73.8575914.
- Dandekar bounds: `73.842,18.498,73.850,18.506`. The [Dandekar Bridge bus stop](https://mapcarta.com/N1054647784) is at 18.50112, 73.84666; the [mapped bridge road](https://in.geoview.info/dandekar_bridge,199637794w) is approximately 18.50208, 73.84552.
- These small exploratory boxes were chosen around the mapped anchors to query existing street imagery. They are not official SRA boundaries, and the exact building in the [original article](https://indianexpress.com/article/cities/pune/slum-dwellers-relocated-city-dumps-sanitation-cleanliness-10274974/) has not been matched to imagery. Article claims were not used as labels.

## Content decision

Dhankawadi's newest returned image is from February 2018. No images meet the existing freshness requirement, so no sample download was warranted.

Dandekar's 15 samples contain five no-clear-target observations, four limited-visibility frames, three uncertain scattered-litter observations and three unusable frames. No clear dump or overflowing bin was identified. See the [visual review](../../visual-review/pune-dandekar-bridge/review.md) and [gallery](../../visual-review/pune-dandekar-bridge/index.html). This is a sample-based rejection, not proof that all 465 recent frames lack waste.

## Reproduction

Use the configuration snapshot in this folder to reproduce these bounds:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-072617/candidate-config.json
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-072617/pune_dandekar_bridge-images.json -OutputFolder reports/visual-review/pune-dandekar-bridge -PerSequence 3
```

The freshness cutoff advances on a rerun; the saved summary records this run's cutoff. Source metadata, config snapshot, sample manifest and review notes are retained. No credentials are included in this report.

**Next queued work:** resolve and screen Poona Hospital / Two-Wheeler Bridge (entry 4). Full annotation and training remain on hold.
