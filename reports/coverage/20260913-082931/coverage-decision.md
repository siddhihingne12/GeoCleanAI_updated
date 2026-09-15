# Pune Hadapsar market-edge screening, round 4

Checked 13 September 2026. **Metadata passes; initial image review does not establish training positives. Corridor not approved.**

| Check | Result |
|---|---:|
| Unique image records | 1,468 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 717 |
| Recent frames after approximately 5 m spacing | 584 |
| Recent sequences after spacing | 6 |
| Sequence-centroid clusters | 6 |
| Oldest / newest capture | 2018-11-24 / 2026-03-21 |
| Completed search cells | 24/24 |
| Downloaded and individually reviewed samples | 18 |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

All cells completed without recorded failures or pagination caps. Counts describe this rectangle only. Six centroid clusters approximate route separation; they do not establish six waste sites or independent evaluation groups.

## Location and bounds

Bounds in west/south/east/north order: `73.931,18.497,73.943,18.505`. This exploratory rectangle covers selected public-road approaches around Mantri Market Road and Gadital, not all Hadapsar.

Location anchors: [Mantri Market Road address coordinates](https://www.pataitihaas.com/mantri-market-rd-hadapsar-gaon-hadapsar-pune-maharashtra-411028-india), 18.5009, 73.9347; and [Hadapsar Gadital PMPML Bus Stand](https://www.latlong.net/poi/hadapsar-gadital-pmpml-bus-stand-473347), 18.5002932, 73.9392. These directory coordinates support search placement, not surveyed boundaries or waste labels.

## Content decision

The 18 perspective samples contain three no-clear-target observations, eight limited-visibility frames, two potential difficult negatives, one scattered-litter observation and four unusable frames. No confirmed positive was found for either class. Market goods, sparse litter and broken road material were not relabelled to fill quotas.

The [visual review](../../visual-review/pune-hadapsar-market/review.md) and [gallery](../../visual-review/pune-hadapsar-market/index.html) preserve individual findings. Flyover coverage and camera quality are important limits. The sample result does not establish that every recent image lacks waste.

## Reproduction and next step

The saved `candidate-config.json` preserves this round's bounds. Run `Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-082931/candidate-config.json`. Sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-082931/pune_hadapsar_market-images.json -OutputFolder reports/visual-review/pune-hadapsar-market -PerSequence 3`. Use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` to invoke scripts where needed. Freshness advances on rerun; the summary preserves this run's cutoff.

Next queued lead: entry 6, Dhole Patil Road. No annotation or training has started. Across five review folders, 146 sample records now have individual notes.
