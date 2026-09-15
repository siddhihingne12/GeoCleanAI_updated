# Pune Dhole Patil Road screening, round 5

Checked 13 September 2026. **Metadata passes; initial image review does not establish training positives. Corridor not approved.**

| Check | Result |
|---|---:|
| Unique image records | 1,007 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 517 |
| Recent frames after approximately 5 m spacing | 367 |
| Recent sequences after spacing | 21 |
| Sequence-centroid clusters | 13 |
| Oldest / newest capture in the rectangle | 2018-10-19 / 2026-03-23 |
| Completed search cells | 20/20 |
| Downloaded and individually reviewed samples | 52 |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

All cells completed without recorded failures or pagination caps. Counts describe this rectangle only. Thirteen centroid clusters approximate route separation; they do not establish 13 waste sites or independent evaluation groups.

## Location and bounds

Bounds in west/south/east/north order: `73.871,18.531,73.881,18.539`. This exploratory rectangle covers selected public-road edges around Dhole Patil Road and the Ruby Hall Clinic vicinity, not all of Sangamvadi or central Pune.

Location anchors: [Dhole Patil Road mapped point](https://www.findlatitudeandlongitude.com/l/Dhole%2BPatil%2BRoad%2C%2BPune%2B-%2B411001%2C%2B/3666551/), 18.534989, 73.87618; [Ruby Hall Clinic coordinate listing](https://www.latlong.net/poi/ruby-hall-clinic-398833), 18.5335374, 73.8771538; and the [Ruby Hall Clinic official contact page](https://rubyhall.com/contact-us/), which lists 40 Sassoon Road, Sangamvadi. These sources support search placement, not surveyed boundaries or waste labels.

## Content decision

The 52 samples contain 22 no-clear-target observations, 12 limited-visibility frames, three difficult construction-material negatives and 15 unusable frames. No confirmed positive was found for either class. A closed litter bin, paving blocks, construction rubble, sparse leaves and isolated scraps were not relabelled to fill quotas.

The [visual review](../../visual-review/pune-dhole-patil-road/review.md) and [gallery](../../visual-review/pune-dhole-patil-road/index.html) preserve individual findings. Traffic, close billboards, camera aim, occlusion and motion blur are important limits. The sample result does not establish that every recent image lacks waste.

## Reproduction and next step

The saved `candidate-config.json` preserves this round's bounds. Run `Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-115520/candidate-config.json`. Sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-115520/pune_dhole_patil_road-images.json -OutputFolder reports/visual-review/pune-dhole-patil-road -PerSequence 3`. Use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` to invoke scripts where needed. Freshness advances on rerun; the summary preserves this run's cutoff.

Next queued lead: entry 7, Kondhwa / NIBM corridor. No annotation or training has started. Across six review folders, 198 sample records now have individual notes.
