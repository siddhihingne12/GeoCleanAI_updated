# Kasba - Mangalwar - Raviwar belt visual review - 12 September 2026

**Decision: do not approve this candidate as the training corridor.** It passed the metadata gate but fails the image-content gate on two independent grounds: no clear positive examples of either project class, and a capture population too heterogeneous and too geographically concentrated to support the planned dataset or a leakage-free split. Keep the downloaded material as negative examples and as test material for the panorama/perspective and orientation work. Continue down [the Pune search queue](../../../PUNE_SEARCH_PLAN.md) from entry 3. No field collection or self-capture is requested.

## Sample and evidence

- Inspected **all 43 downloaded samples**, drawn from all 23 recent sequences in the candidate.
- Sampling: frames restricted to the last 24 months, then up to three per sequence at even positions within each sequence, ordered by capture timestamp and image ID. Sequences shorter than three frames contribute their available frames only. This is deterministic sampling, not a representative estimate of waste prevalence.
- Capture dates in the sample span 25 January 2025 to 4 August 2026. These are platform metadata, not independently verified dates.
- Downloaded the API's 2048 thumbnail variant; source JPEGs are unmodified. Contact sheets are inspection aids, not training images.
- Per-image observations are in `review-notes.json`; sequence, date, camera position, contributor and source links are in `manifest.json`.

## Findings

| Finding | Images |
|---|---:|
| Clear `roadside_dump` identified | **0** |
| Clear `overflowing_bin` identified | **0** |
| Weak accumulation, one physical site, below label threshold | 2 |
| Uncertain scattered litter, no accumulation | 4 |
| Difficult negative candidate | 1 |
| No clear target observed | 26 |
| Unusable: camera aim, image quality, or occlusion | 10 |

These rows partition the 43-image review. "No clear target" observations are not certified clean labels; distant, shaded or obstructed objects may not resolve at this review size. This review does not establish that no waste exists in the candidate area.

The single most dump-like observation is a street electrical cabinet with refuse banked at its base and against the adjoining wall (`931651069200518`, repeated in `682190771646504`). It is small in extent and does not meet the bar for a `roadside_dump` label. Notably it is the **same physical corner** reached by five different sequence IDs — see below.

Difficult negative worth keeping:

- `3894609967504755`: construction hoarding with a DANGER / work-in-progress sign, rubble, soil and white bags at its base. Visible context indicates construction activity, not household waste.

## Why the imagery does not form a usable training domain

The metadata gate counted frames and sequence IDs. Inspection shows the recent population is five unrelated capture styles, not one corridor survey:

| Sequence | Frames | Date | Capture style | Usable for ground-level waste |
|---|---:|---|---|---|
| `doXFjK0Shsn1tHWPvOaIM2` | 237 | 2026-01-19 | Car dashcam, forward, through windshield | Yes; roadside appears small and oblique at the frame edges |
| `LeBtoM2r3HnDdgUPmCuS1G` | 172 | 2026-02-01 | Side and upward, aimed at facades and canopy | Largely no; ground plane mostly out of frame |
| `2MzIJGcVaDHhbw7oAvqsO3` | 119 | 2026-03-06 | Side window at dusk, sill occlusion, motion blur | Largely no |
| `gKGieboXkcMf0YBwSJ7CzD` | 48 | 2025-01-25 | Handheld walking, market | Yes, best ground detail; heavy pedestrian occlusion; different domain |
| `ciCudy2xvPoZrqpS9z8Rnj` | 44 | 2026-03-01 | Two-wheeler mount aimed low at the road surface | Marginal; ~60% tarmac, motion blur |

The four route-scale captures differ in mounting height, pitch, field of view, lighting and motion blur. Training one detector across them, and reasoning about pixel-to-bearing geometry across them, are separate problems the blueprint does not currently budget for. The upward-aimed and dusk sequences together account for 291 of 659 recent frames, or 44%, that contribute little ground coverage.

## Sequence IDs do not equal independent routes or places

Merging sequence centroids within 40 m:

- **23 recent sequence IDs resolve to 13 distinct physical locations.**
- 620 of 659 recent frames, 94%, belong to just four route-scale captures.
- `2MzIJGcVaDHhbw7oAvqsO3` and `ciCudy2xvPoZrqpS9z8Rnj` have centroids about 20 m apart with ~180 m extents each: the same road segment captured twice, on 1 and 6 March 2026.
- Eighteen sequence IDs are single-ride fragments, nearly all dated 2026-02-06, each holding 1 to 11 frames and together only ~29 frames. Three of them (`He3asv2S`, `mWbSu9Qr`, `ZjlzYhJo`) sit at the **identical coordinate** 73.8658, 18.5221. Five (`l9tBfaYj`, `dgJW1mZi`, `9PjOdS8M`, `OsgJe9r5`, `pgnlWU26`) sit at 73.8613, 18.5191.

The consequence is concrete: the one weak accumulation site in the entire sample lies at 73.8613, 18.5191 and is seen through five different sequence IDs. A split on sequence ID would place the same physical site in both training and test. **The blueprint's "≥ 3 distinct sequences" gate is satisfied numerically and meaningless in substance here.** Gate on distinct physical sites instead; `Measure-MapillaryCoverage.ps1` now reports that figure.

## Against the annotation plan

The plan requires at least 200 labelled images, targeting 100-150 dump-positive, 50-80 bin-positive and 50-80 difficult negatives, across sites separable for evaluation. This sample yields zero confirmed positives of either class and one weak accumulation site. Nothing here supports those counts, and denser sampling of the same five captures would resample the same 13 locations rather than discover new sites.

## Next deliverable

Coverage and content screening for Pune search-queue entry 3: the specific SRA leads, beginning with Shankar Maharaj Vasahat in Dhankawadi and the Dandekar Bridge locality, with public-road bounds resolved on the map before querying. Report distinct physical sites alongside frame and sequence counts. No corridor is approved.
