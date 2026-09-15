# Pune Kondhwa - NIBM corridor screening, round 6

Checked 13 September 2026. **Metadata passes; initial image review does not establish training positives. Corridor not approved.**

| Check | Result |
|---|---:|
| Unique image records | 444 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 369 |
| Recent frames after approximately 5 m spacing | 323 |
| Recent sequences after spacing | 9 |
| Sequence-centroid clusters | 5 |
| Oldest / newest capture in the rectangle | 2017-11-19 / 2025-12-24 |
| Completed search cells | 32/32 |
| Downloaded and individually reviewed samples | 17 |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

All cells completed without recorded failures or pagination caps. Counts describe this rectangle only. Five centroid clusters approximate route separation; they do not establish five waste sites or independent evaluation groups.

## Location and bounds

Bounds in west/south/east/north order: `73.887,18.472,73.902,18.480`. This exploratory rectangle covers a compact section of NIBM Road, Kondhwa Khurd and public-road approaches to the National Institute of Bank Management. It does not cover all of Kondhwa.

Location anchors: [Kondhwa mapped point](https://www.latlong.net/place/kondhwa-pune-maharashtra-india-18204.html), 18.477091, 73.890686; [NIBM Road mapped point](https://www.coordinatesfinder.com/coordinates/576639-nibm-road-pune), 18.4777776, 73.8931128; [NIBM campus map point](https://mapcarta.com/34491220), 18.47533, 73.89972; and the [NIBM official contact page](https://www.nibmindia.org/ContactUS/), which lists NIBM Post Office, Kondhwa Khurd, Pune 411048. These sources support search placement, not surveyed boundaries or waste labels.

## Content decision

The 17 samples contain 10 no-clear-target observations, two limited-visibility frames, three uncertain scattered-litter frames and two unusable frames. No confirmed positive was found for either class. Sparse verge litter and an ordinary non-overflowing service bin were not relabelled to fill quotas.

The [visual review](../../visual-review/pune-kondhwa-nibm/review.md) and [gallery](../../visual-review/pune-kondhwa-nibm/index.html) preserve individual findings. Night capture, glare, traffic and blur are important limits. Two image IDs from separate short sequences show a duplicated junction view. The sample result does not establish that every recent image lacks waste.

## Reproduction and next step

The saved `candidate-config.json` preserves this round's bounds. Run `Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-122001/candidate-config.json`. Sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-122001/pune_kondhwa_nibm-images.json -OutputFolder reports/visual-review/pune-kondhwa-nibm -PerSequence 3`. Use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` to invoke scripts where needed. Freshness advances on rerun; the summary preserves this run's cutoff.

Next queued lead: entry 8, Shivajinagar. No annotation or training has started. Across seven review folders, 215 sample records now have individual notes.
