# Pune panorama candidate survey — 25 September 2026

The first 500 m search checked five points and found six panoramas near central Pune. A later survey used 1.5 km radii at 15 sample points and found **194 unique panorama records**. This is a sample of the demo area, not a citywide inventory. Aundh returned the 100-image API limit, so more may exist there. Four area requests failed and must not be counted as zero coverage. The raw response summary is in the ignored local file `artifacts/pune-survey.json`; rerun `scripts/survey_pune.py` to refresh it.

Twelve candidate panoramas from several road segments and capture dates were initially downloaded at 2048 × 1024 and visually inspected. Ten were usable street scenes for further review; the other two were difficult examples. Original panoramas were later downloaded and projected into 72 views. The user completed all decisions: 18 litter, 30 clean and 24 skipped views. The 48 included views are reserved for evaluation at `data/pune-test-v1/`. The table below records the initial survey observations, before those labels were added.

| Mapillary image | Captured | Contributor | Capture sequence | Visual review |
|---|---|---|---|---|
| [1007824738196605](https://www.mapillary.com/app/?pKey=1007824738196605) | 6 May 2025 | skysign | `kj3QPyEBUCMsxe8a5KJrOq` | Usable street panorama; no confirmed litter label yet. |
| [671858045596844](https://www.mapillary.com/app/?pKey=671858045596844) | 6 May 2025 | skysign | `kj3QPyEBUCMsxe8a5KJrOq` | Usable intersection panorama; same sequence as previous image. |
| [1519250783014866](https://www.mapillary.com/app/?pKey=1519250783014866) | 17 Apr 2026 | skysign | `XTED9drvwLtVUa0b7I3xkF` | Usable divided-road panorama. |
| [1592740594738835](https://www.mapillary.com/app/?pKey=1592740594738835) | 14 Feb 2025 | skysign | `urjFt3abM27mIsnl5JyvWA` | Usable road and flyover panorama. |
| [1275678281102866](https://www.mapillary.com/app/?pKey=1275678281102866) | 28 Apr 2026 | skysign | `72h3Bl0PzTijgZecxVOMA6` | Usable street panorama; roadside rubble needs a clear in-scope/out-of-scope decision. |
| [992634033586014](https://www.mapillary.com/app/?pKey=992634033586014) | 28 Apr 2026 | skysign | `72h3Bl0PzTijgZecxVOMA6` | Usable street panorama; same sequence as previous image. |
| [4474864412761647](https://www.mapillary.com/app/?pKey=4474864412761647) | 28 Apr 2026 | skysign | `72h3Bl0PzTijgZecxVOMA6` | Usable shaded street panorama; same sequence as previous two images. |
| [2019246628892375](https://www.mapillary.com/app/?pKey=2019246628892375) | 17 Sep 2025 | skysign | `BEohfHsAZiWFlVXwp7Gz4N` | Usable road panorama near a flyover. |
| [1071444336886796](https://www.mapillary.com/app/?pKey=1071444336886796) | 1 Jul 2017 | tranzitnotes | `x6rXAj7a1lCzSbeZFcGktD` | Busy junction, lower contrast; inspect possible small roadside litter. |
| [648227600042863](https://www.mapillary.com/app/?pKey=648227600042863) | 1 Jul 2017 | tranzitnotes | `WHdS48wTFr6RbkAEDnMet1` | Busy street; apparent waste near the left curb needs box-level review. |
| [207405678297886](https://www.mapillary.com/app/?pKey=207405678297886) | 27 Jan 2019 | tranzitnotes | `3cvhCQx0tqFsoYT62MALIJ` | Fort courtyard; keep as a possible clean or out-of-domain example. |
| [187603527137174](https://www.mapillary.com/app/?pKey=187603527137174) | 1 Jul 2017 | tranzitnotes | `kNFM9Tp7XGgbvwEznVq5Uc` | Night and rain; keep as a difficult visibility example. |

Mapillary provides the photographs. Display each contributor, capture date and source link when presenting imagery, following [Mapillary's CC BY-SA attribution guidance](https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data). Keep images from the same sequence, and visually similar views from nearby sequences, in the same training or evaluation split.

The recent captures are mostly wide roads with little clearly visible litter at thumbnail scale. They can help test false alarms after human review, but they do not yet provide enough confirmed positive litter examples to measure an 85% recall target. Review original images and collect more litter-positive Pune scenes before forming the held-out test set.
