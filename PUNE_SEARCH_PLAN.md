# GeoClean AI V2 - Pune study-area replacement

Updated 13 September 2026. This is the active location-selection plan and replaces the proposed PCMC Area A follow-up, the Area B training-corridor preference, and the self-capture contingency.

## Decision and fixed scope

**Superseded for training data on 13 September 2026 by [scope decision E + A](#scope-decision---e--a-13-september-2026):** the detector now trains on openly licensed public datasets, and Pune Mapillary imagery serves as a diagnostic set. The paragraph below records the original corridor-search scope.

Use existing Mapillary street-level imagery from the user's Pune shortlist. Select one final road corridor after both coverage and image-content checks pass. Searching several neighbourhoods does not make this a citywide detection study.

Keep two classes: `roadside_dump` and `overflowing_bin`. Keep OpenStreetMap, local CVAT, offline inference, PostGIS, FastAPI and the React inspection dashboard. The project remains a fresh build with a four-week prototype target and remote evaluation. No field collection, self-capture or manual collection of municipal reports is required.

PCMC results are historical feasibility evidence. Preserve their images and notes as possible negative examples and image-processing test material. Do not overwrite their coordinates or rename those results as Pune coverage.

## Search queue

This is a work order based on the user's leads and a manageable search scope, not a ranking of neighbourhood cleanliness. **All ten entries have now been screened.**

| Order | Lead | Initial focus and limits |
|---|---|---|
| ~~1~~ | ~~Bhavani Peth~~ | **Screened 12 Sep 2026 - REJECTED, stale coverage.** 589 images, all captured 2016-02 to 2019-10, zero inside the 24-month window. [Coverage decision](reports/coverage/20260912-145227/coverage-decision.md). Retain as geometry test material only. |
| ~~2~~ | ~~Kasba / Mangalwar / Raviwar / Nana Peth~~ | **Screened 12 Sep 2026 - REJECTED on image content.** Metadata gate passed (452 spaced recent frames, newest 2026-08-04) but all 43 sampled frames yielded zero clear positives of either class, and the 23 sequence IDs resolve to only 13 distinct locations across five unrelated capture styles. [Visual review](reports/visual-review/pune-kasba-belt/review.md). |
| ~~3~~ | ~~Specific SRA colonies and nearby public lanes~~ | **Screened 13 Sep 2026.** Shankar Maharaj Vasahat vicinity: 139 images, zero recent. Dandekar Bridge vicinity: 412 spaced recent frames, but zero clear positives in 15 reviewed samples. Neither approved. [Round 2 decision](reports/coverage/20260913-072617/coverage-decision.md). Exact article building not matched. |
| ~~4~~ | ~~Poona Hospital / Two-Wheeler Bridge~~ | **Screened 13 Sep 2026.** 805 spaced recent frames, 15 sequences and 12 route-centroid clusters; zero clear positives in 43 samples. Not approved. [Round 3 decision](reports/coverage/20260913-073542/coverage-decision.md). |
| ~~5~~ | ~~Hadapsar~~ | **Screened 13 Sep 2026.** Mantri Market - Gadital bounds: 584 spaced recent frames, six sequences/clusters; zero clear positives in 18 samples. Not approved. [Round 4 decision](reports/coverage/20260913-082931/coverage-decision.md). This does not cover all Hadapsar. |
| ~~6~~ | ~~Dhole Patil Road~~ | **Screened 13 Sep 2026.** Ruby Hall vicinity bounds: 367 spaced recent frames, 21 sequences and 13 route-centroid clusters; zero clear positives in 52 samples. Not approved. [Round 5 decision](reports/coverage/20260913-115520/coverage-decision.md). |
| ~~7~~ | ~~Kondhwa / NIBM corridor~~ | **Screened 13 Sep 2026.** Compact NIBM Road bounds: 323 spaced recent frames, nine sequences and five route-centroid clusters; zero clear positives in 17 available samples. Not approved. [Round 6 decision](reports/coverage/20260913-122001/coverage-decision.md). |
| ~~8~~ | ~~Shivajinagar~~ | **Screened 13 Sep 2026.** Emerson Tower - Patil Estate bounds: 1,145 spaced recent frames, 11 sequences and four route-centroid clusters; zero clear positives in 47 distinct reviewed images after focused adjacent-frame checks. Stored workshop material and construction rubble were retained as hard negatives. Not approved. [Round 7 decision](reports/coverage/20260913-124627/coverage-decision.md). |
| ~~9~~ | ~~Pashan / Aundh / Baner~~ | **Screened 13 Sep 2026 as three separate areas.** Pashan: 51 spaced recent frames from one dashcam drive, metadata FAIL. Baner Gaon: newest capture 2024-03-20, zero recent, metadata FAIL. Aundh: 474 spaced recent frames, 14 sequences, nine clusters, metadata PASS; 60 distinct reviewed images show **one confirmed roadside-dump site** (eight consecutive frames) and zero overflowing bins. None approved. [Round 8 comparison](reports/coverage/round-8-comparison.md). |
| ~~10~~ | ~~Fursungi-Uruli waste-site surroundings~~ | **Screened 13 Sep 2026.** Interpreted as the Uruli Devachi / Phursungi waste-depot locality per the CPCB committee report. 269 images, all captured 2020-12-26 in three sequences; zero recent, metadata FAIL. Landfill interiors, burning and leachate remained out of scope. [Coverage decision](reports/coverage/20260913-132853/coverage-decision.md). |

## Execution steps

1. Resolve the first two search areas against map landmarks and road names. Save source links, coordinates and explicit west/south/east/north bounds. Do not reuse the PCMC coordinates in the existing scripts.
2. Query Mapillary in small cells, follow pagination, deduplicate by image ID and record incomplete queries. Collect capture dates, sequences, camera positions, headings, dimensions and available calibration metadata.
3. Apply the last-24-month filter and approximately five-metre spacing. Require at least 300 metadata-eligible recent frames across at least three **distinct physical locations**, not three sequence IDs. Round 1 showed the two are far apart: 23 recent sequence IDs in the Kasba belt resolved to 13 locations, with three sequence IDs sharing one identical coordinate. `Measure-MapillaryCoverage.ps1` now reports `distinct_sites` and gates on it. A count pass is provisional until image quality is reviewed.
4. Download three evenly distributed samples per sequence for each promising candidate. Inspect actual waste, camera obstructions, resolution and panorama handling. If targets are found, inspect additional frames and neighbouring viewpoints, up to nine distributed samples per sequence for the screening round.
5. Record clear positives, uncertain objects, difficult negatives and unique candidate sites separately. Repeated frames of the same dump are not separate sites. Construction work, shop goods, leaves, ordinary bins and scattered litter must not be relabelled to fill class quotas.
6. Select a corridor only when the reviewed imagery and follow-up frames can support the planned annotation set: at least 200 labelled images, targeting 100-150 dump-positive images, 50-80 overflowing-bin-positive images and 50-80 difficult negatives. Aim for approximately 250 total where feasible; overlapping positive classes in one image must be documented. Confirm physical-site and sequence separation for evaluation.
7. If a candidate lacks recent coverage or positives, record the reason and move down the queue. Stop expanding once one suitable corridor is established. If none works, report the data constraint and request a specific scope decision; do not silently switch to field collection, a single class, older data or unrelated datasets.

Implementation note, updated 13 September 2026: the tooling is parameterized and round 8 has run.

- `Measure-MapillaryCoverage.ps1` reads candidates via `-CandidateConfig`, and reports `distinct_sites` alongside sequence counts. Round 8 used one config per area (`config/pune-pashan-candidates.json`, `config/pune-aundh-candidates.json`, `config/pune-baner-candidates.json`, `config/pune-fursungi-uruli-candidates.json`); `config/pune-candidates.json` still holds round 7.
- `Get-MapillaryReviewSample.ps1` takes `-MetadataFile`, `-OutputFolder` and `-SinceMonths` (default 24, so review effort never lands on frames the coverage gate already excluded), and caps per-sequence samples at the frames actually available. It also accepts `-SequenceId` for focused route review and `-FocusImageId` for a compact temporal window around an ambiguous frame. `-PerSequence 1` with `-FocusImageId` fetches one exact frame, which round 8 used for the persistence check. Each run overwrites `manifest.json` in its output folder, so give each focused run its own folder.
- `Build-ReviewGallery.ps1` takes `-ReviewFolder`, `-Heading` and `-Summary`. Round 8 added the finding tags `roadside_dump_positive`, `roadside_dump_candidate` and `overflowing_bin_positive`; previously any positive would have been labelled "No clear target observed".

Add each new candidate to the config with its anchors and sources rather than editing coordinates inline. Keep all historical reports separate.

Screening lesson from round 1: a metadata pass says nothing about camera aim. Both rejected candidates had complete metadata; the Kasba belt's recent frames turned out to be a car dashcam, an upward-aimed facade survey, a dusk side-window ride, a handheld market walk and a low-aimed two-wheeler mount. Check camera aim and ground coverage in the first few samples of each sequence before sampling it densely.

Screening lesson from round 8: in 2,048 px spherical panoramas a genuine dump can occupy about 130 px and read as clutter at full-frame view. Zoom into verges beside railings, walls and bridge approaches before recording "no clear target".

## Acceptance and reporting

- Coverage and target visibility are separate gates. A neighbourhood reputation, settlement type or news story is not a training label.
- Keep the original target of at least 15 distinct mapped candidate waste sites, reporting supporting image dates and location method.
- Remote checks measure approximate agreement with defensible map reference points, with uncertainty stated. Do not claim field-verified accuracy or a current live waste inventory.
- Document deliberate searching for waste-positive scenes. Evaluation on this selected corridor cannot establish a citywide waste rate or a Pune-versus-PCMC cleanliness comparison.
- Week 1 remains corridor selection, imagery preparation and the small geometry trial; week 2 annotation and baseline training; week 3 geolocation/API/dashboard; week 4 evaluation, reporting and two buffer days. Rebaseline the schedule if positive-example discovery exceeds week 1.

## Source review

The user's sources are search leads, not requirements for additional user-collected reports.

- [Pune City Sanitation Plan, Scribd copy](https://www.scribd.com/document/102719474/Pune-CSP): the text describes baseline collection beginning in November 2010 and references 2011-12 budgets. Use it as historical planning context, not evidence of current ward rankings or current visible waste. Its age does not prove that any listed location is unsuitable; the imagery must decide.
- [Indian Express, 27 September 2025](https://indianexpress.com/article/cities/pune/slum-dwellers-relocated-city-dumps-sanitation-cleanliness-10274974/): the accessible article concerns sanitation around SRA housing, mentions the Dandekar Bridge locality and captions a photograph at Shankar Maharaj Vasahat in Dhankawadi. It does not substantiate the supplied Fursungi-Uruli leachate claim.
- [Supplied Facebook post](https://www.facebook.com/dcnenglish/posts/residents-have-raised-serious-allegations-against-the-pune-municipal-corporation/1001441032716994/): content could not be retrieved during this check. The associated Pashan/Aundh/Baner claim remains unverified; the round 8 imagery neither confirms nor tests it.
- [CPCB committee report to the NGT](https://www.greentribunal.gov.in/sites/default/files/news_updates/Committee%20Report%20filed%20by%20CPCB%20in%20EA.No_.%2002-2021%20%28page%20nos.%2069-108%29.pdf): identifies Devachi Urali and Phursungi waste-depot survey plots; used only to place the queue entry 10 search rectangle.
- Other location and cleanliness descriptions are user-supplied leads without directly inspected supporting sources. Retain them in the queue without repeating allegations about residents or making citywide cleanliness claims.

## Progress

**Rounds 1-8 complete, latest 13 September 2026. All ten queue entries screened. No corridor is approved.**

| Candidate | Metadata gate | Content gate | Outcome |
|---|---|---|---|
| Bhavani Peth - Nana Peth | FAIL (0 recent frames) | not run | Rejected: coverage ends October 2019 |
| Kasba - Mangalwar - Raviwar belt | PASS (452 frames, 13 sites) | FAIL (0 clear positives) | Rejected: no positives, incoherent capture population |
| Shankar Maharaj Vasahat / Dhankawadi vicinity | FAIL (0 recent frames) | not run | Rejected: latest returned capture February 2018 |
| Dandekar Bridge vicinity | PASS (412 frames, 4 route-centroid clusters) | FAIL (0 clear positives in 15 samples) | Not approved after initial sample review |
| Poona Hospital / Two-Wheeler Bridge vicinity | PASS (805 frames, 12 route-centroid clusters) | FAIL (0 clear positives in 43 samples) | Not approved after initial sample review |
| Hadapsar Mantri Market - Gadital | PASS (584 frames, 6 route-centroid clusters) | FAIL (0 clear positives in 18 samples) | Not approved after initial sample review |
| Dhole Patil Road - Ruby Hall vicinity | PASS (367 frames, 13 route-centroid clusters) | FAIL (0 clear positives in 52 samples) | Not approved after initial sample review |
| Kondhwa - NIBM Road corridor | PASS (323 frames, 5 route-centroid clusters) | FAIL (0 clear positives in 17 samples) | Not approved after initial sample review |
| Shivajinagar - Emerson Tower and Patil Estate | PASS (1,145 frames, 4 route-centroid clusters) | FAIL (0 clear positives in 47 distinct reviewed images) | Not approved after initial and adjacent-frame review |
| Pashan - Sutarwadi Road and village approaches | FAIL (51 frames, 1 site) | supplementary only (0 positives in 3 samples) | Rejected: one dashcam drive on the highway edge. [Decision](reports/coverage/20260913-131135/coverage-decision.md) |
| Aundh - Parihar Chowk, Bremen Chowk and Gaon approaches | PASS (474 frames, 9 route-centroid clusters) | FAIL (1 dump site in 8 frames, 0 bins, 60 distinct reviewed images) | Not approved: first confirmed Pune positive, but one site and no second class. [Decision](reports/coverage/20260913-131200/coverage-decision.md) |
| Baner Gaon - Baner Road | FAIL (0 recent frames) | not run | Rejected: newest capture March 2024. [Decision](reports/coverage/20260913-131205/coverage-decision.md) |
| Fursungi - Uruli Devachi depot surroundings | FAIL (0 recent frames) | not run | Rejected: one capture day, December 2020. [Decision](reports/coverage/20260913-132853/coverage-decision.md) |

Eight Pune candidates have passed on counts; seven failed with zero positives and Aundh failed with one dump site and no overflowing bins. Historical PCMC Area B also failed its sample review. Positive-example availability, not frame availability, is the binding constraint. The reported centroid clusters approximate route separation, not confirmed waste sites. Across all completed review work, 325 distinct sample images now have individual findings; repeated viewpoints and sequences are not independent sites.

## Scope decision - E + A, 13 September 2026

The plan's stopping condition was met: entries 9 and 10 lacked suitable coverage or positives, and the queue is exhausted. Across all rounds the searched imagery contains one confirmed roadside-dump site and zero overflowing bins, against a requirement of at least 15 sites and both classes. The options are set out in the [round 8 comparison](reports/coverage/round-8-comparison.md).

**The user chose E + A:**

- **E**: train the detector on existing, openly licensed public datasets for both classes instead of Pune Mapillary positives.
- **A**: report the Mapillary positive-scarcity result as a documented project finding.

What this changes:

- **The corridor search is closed.** Do not add queue entries or rerun screening unless the user reopens it.
- **Training data comes from public sources.** Candidates, licences and gaps are in the [public dataset review](reports/dataset-review.md). `roadside_dump` is feasible, including a CC BY 4.0 Pune dataset (QR4Change) that needs boxes drawn. `overflowing_bin` has no verified openly licensed box dataset yet; it depends on inspecting a Roboflow export or on the user requesting StreetView-Waste access.
- **Pune imagery becomes a diagnostic set, not a benchmark.** The Aundh bridge-railing dump frames (sequence `BEohfHsAZiWFlVXwp7Gz4N`, frames `4192131444349692` through `24511646765122743`, one split group) are the only Pune positive. The hard negatives from rounds 1-8 form a false-positive test.
- **Geolocation is demonstrated as a case study** on the Aundh dump frames plus the synthetic two-camera unit test. The 80%-within-15-m statistic cannot be evaluated from one site.

What does not change: the two class definitions, the 24-month freshness rule for any Pune imagery used, the ban on Google Street View-derived data, local CVAT, and the PostGIS, FastAPI and React deliverables. No annotation or training has started.

Retain the Aundh bridge-railing dump frames (sequence `BEohfHsAZiWFlVXwp7Gz4N`, frames `4192131444349692` through `24511646765122743`) as a single split group, together with the hard negatives recorded across rounds, whichever option is chosen.
