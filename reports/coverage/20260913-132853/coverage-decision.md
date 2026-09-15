# Pune Fursungi - Uruli Devachi depot surroundings screening, round 8d (queue entry 10)

Checked 13 September 2026. **Metadata gate fails: all imagery comes from one day in December 2020. Rejected; content review not possible.**

| Check | Result |
|---|---:|
| Unique image records | 269 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 0 |
| Recent frames after approximately 5 m spacing | 0 |
| Recent sequences / sequence-centroid clusters | 0 / 0 |
| All sequences in the rectangle | 3 |
| Oldest / newest capture in the rectangle | 2020-12-26 / 2020-12-26 |
| Completed search cells | 100/100 |
| Images individually reviewed | 0 |

All 100 search cells completed without recorded failures or pagination caps. All 269 images are perspective imagery with camera parameters, compass and corrected position. Even without the freshness window, 269 frames from three sequences on one day would not satisfy the 300-frame, three-site gate.

## Interpretation of the lead

Queue entry 10 asked whether Uruli Devachi was intended. This round treats the lead as the Uruli Devachi / Phursungi municipal waste-depot locality, because the [CPCB committee report to the NGT](https://www.greentribunal.gov.in/sites/default/files/news_updates/Committee%20Report%20filed%20by%20CPCB%20in%20EA.No_.%2002-2021%20%28page%20nos.%2069-108%29.pdf) identifies Devachi Urali and Phursungi waste-depot survey plots. Only public-road waste matching `roadside_dump` or `overflowing_bin` would have been relevant. Landfill interiors, burning and leachate remain out of scope.

## Location and bounds

Bounds in west/south/east/north order: `73.944,18.454,73.964,18.474`, a roughly 2.1 km by 2.2 km rectangle around the depot and its road approaches.

Location anchors: the [published dumping-yard centre](https://www.researchgate.net/publication/360882884_Groundwater_quality_assessment_in_proximity_to_solid_waste_dumpsite_at_Uruli_Devachi_in_Pune_Maharashtra), converted from DMS to 18.47111, 73.95361 and used only as an approximate anchor; and [Uruli Devachi locality](https://mapcarta.com/29229622) at 18.45584, 73.95645. These support search placement, not surveyed boundaries or waste labels.

## Reproduction

`Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-132853/candidate-config.json`. The review sampler refuses this candidate because no frames survive the freshness filter. Freshness advances on rerun; the summary preserves this run's cutoff.
