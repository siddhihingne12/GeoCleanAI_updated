# Round 8 comparison - Pashan, Aundh, Baner and Fursungi-Uruli Devachi

Compiled 13 September 2026. Covers queue entries 9 and 10, the last two entries in the Pune search queue.

**Result: none of the four areas can support the two training classes. The search queue is exhausted, so the plan's decision point applies: the data constraint is the project finding, and a scope decision is needed before work continues.**

## Side by side

| | Pashan | Aundh | Baner Gaon | Fursungi - Uruli Devachi |
|---|---|---|---|---|
| Bounds (W,S,E,N) | 73.780,18.533,73.797,18.545 | 73.804,18.557,73.817,18.569 | 73.780,18.556,73.792,18.566 | 73.944,18.454,73.964,18.474 |
| Search cells completed | 54/54 | 42/42 | 30/30 | 100/100 |
| Unique images | 2,442 | 3,220 | 1,408 | 269 |
| Newest capture | 2026-01-12 | 2026-05-19 | 2024-03-20 | 2020-12-26 |
| Recent frames after 5 m spacing | 51 | 474 | 0 | 0 |
| Recent sequences / centroid clusters | 1 / 1 | 14 / 9 | 0 / 0 | 0 / 0 |
| **Metadata gate** (300 frames, 3 sites) | FAIL | PASS | FAIL | FAIL |
| Distinct images reviewed | 3 (supplementary) | 60 | 0 (none eligible) | 0 (none eligible) |
| Roadside-dump sites confirmed | 0 | **1** (8 frames) | - | - |
| Overflowing bins confirmed | 0 | 0 | - | - |
| **Content gate** | not applicable | FAIL | not run | not run |
| Outcome | Rejected: one dashcam drive on the highway edge | Not approved: one dump site, no bins | Rejected: coverage ends March 2024 | Rejected: one 2020 capture day |

Decision records: [Pashan](20260913-131135/coverage-decision.md), [Aundh](20260913-131200/coverage-decision.md), [Baner Gaon](20260913-131205/coverage-decision.md), [Fursungi - Uruli Devachi](20260913-132853/coverage-decision.md).

## What the four results say together

1. **Freshness failed three of four areas.** Baner Gaon's newest capture is almost six months before the cutoff; all 269 Fursungi - Uruli Devachi frames come from one day in December 2020; Pashan's only recent imagery is a one-minute windscreen drive. The large 2019-2023 archives in Pashan and Baner are outside the 24-month window.
2. **Aundh is the only area with usable recent coverage.** Its 474 spaced frames come from eight capture days, dominated by roof-mounted 360-degree cameras repeating one boulevard and river bridge.
3. **Aundh yielded the first confirmed Pune positive:** one roadside dump on the verge of the river-bridge approach railing, visible in eight consecutive frames. It is a single physical site, and its persistence across other dates is inconclusive.
4. **Overflowing bins remain absent.** Across eight Pune rounds, no confirmed overflowing bin has been found.

## Against the annotation requirement

| Requirement | Needed | Best round-8 area (Aundh) |
|---|---:|---:|
| Distinct mapped candidate waste sites | at least 15 | 1 |
| Dump-positive images | 100-150 | 8, all from one site |
| Overflowing-bin-positive images | 50-80 | 0 |
| Difficult negatives | 50-80 | about 9 identified |

A corridor must supply both classes with physical-site separation for evaluation. Aundh falls short on every positive requirement by at least an order of magnitude. Pashan, Baner Gaon and Fursungi - Uruli Devachi contribute nothing usable within the freshness window.

## Cumulative position

- Ten queue entries have been screened across eight rounds; no corridor is approved.
- Distinct reviewed images with individual findings: 262 before this round, 325 after it.
- Confirmed positives across all Pune work: one roadside-dump site and zero overflowing bins.
- Frame availability is not the binding constraint: several areas pass the frame count. Visible, recent, class-matching waste is.

## Decision needed

The plan forbids silently relaxing class definitions, widening the freshness window, substituting field collection or switching data sources. The options below each need an explicit choice; they are listed, not taken.

| Option | What it changes | Main trade-off |
|---|---|---|
| A. Report the data constraint as the finding | Ends the corridor search; documents a negative feasibility result with evidence | No trained detector in the four-week prototype |
| B. Add new search leads beyond the queue | Screens new Pune areas, such as other river-bridge approaches, markets or peri-urban edges, with the same gates | Eight rounds suggest low yield; week 1 is already overrun |
| C. Widen the freshness window, for example to 2019 onward | Reopens the large 2019-2023 Pashan, Baner and Aundh archives | Labels would no longer describe current conditions; weakens the remote-verification claim |
| D. Reduce to one class, `roadside_dump` | Removes the overflowing-bin quota | Changes project scope; one confirmed site is still far below 15 |
| E. Pretrain or supplement with an existing public waste dataset, then evaluate on Pune imagery | Training data no longer depends on Mapillary positives | Domain shift; Pune evaluation still needs local positives to be meaningful |
| F. Targeted self-capture along chosen corridors | Guarantees positives and camera aim | Previously ruled out; needs field time |

**Recommendation, subject to the user's decision:** combine E and A. Train on an existing public dataset for both classes, and use the confirmed Aundh site, the hard negatives collected across eight rounds, and the geometry pipeline for small, honestly scoped Pune inference and localisation tests. Report the Mapillary positive-scarcity result as a documented finding. This preserves the dashboard, PostGIS and FastAPI deliverables without overstating Pune detection accuracy.
