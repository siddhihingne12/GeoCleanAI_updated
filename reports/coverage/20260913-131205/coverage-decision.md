# Pune Baner Gaon screening, round 8c

Checked 13 September 2026. **Metadata gate fails: zero frames inside the 24-month window. Rejected; content review not possible.**

| Check | Result |
|---|---:|
| Unique image records | 1,408 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 0 |
| Recent frames after approximately 5 m spacing | 0 |
| Recent sequences / sequence-centroid clusters | 0 / 0 |
| All sequences in the rectangle | 11 |
| Oldest / newest capture in the rectangle | 2017-08-30 / 2024-03-20 |
| Completed search cells | 30/30 |
| Images individually reviewed | 0 |

All search cells completed without recorded failures or pagination caps. Capture years: 23 frames from 2017, 1,291 from 2019 and 94 from 2024. The newest 2024 capture (20 March) predates the cutoff by almost six months. Camera types are 1,314 perspective and 94 Brown-model images.

## Location and bounds

Bounds in west/south/east/north order: `73.780,18.556,73.792,18.566`. This exploratory rectangle covers Baner Gaon and the adjoining Baner Road. It excludes most of western Baner and Balewadi.

Location anchors: [Baner Gaon mapped locality](https://maps.apple.com/place?auid=13823833336954911597) at 18.55991, 73.78724, a [locality cross-check](https://geographic.org/streetview/india/maharashtra/pune/pune.html) at 18.559003, 73.786763, and the [Baneshwar Cave Temple listing](https://www.showcaves.com/english/in/subterranea/Baneshwar.html) confirming the Baner Gaon address. These support search placement only.

## Reproduction

`Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-131205/candidate-config.json`. The review sampler refuses this candidate because no frames survive the freshness filter. Freshness advances on rerun; the summary preserves this run's cutoff.
