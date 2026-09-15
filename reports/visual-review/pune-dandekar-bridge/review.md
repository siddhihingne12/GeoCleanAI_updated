# Dandekar Bridge sample review - 13 September 2026

**Decision: not approved for training after initial screening.** All 15 downloaded samples, three from each of five recent sequences, were inspected. No clear `roadside_dump` or `overflowing_bin` was established. This does not prove that the area or the remaining frames contain no waste.

## Evidence

The coverage scan returned 1,221 image records, including 465 within the last 24 months and 412 after approximately five-metre spacing. All recent images are perspective captures. The five sequences form four clusters under the script's 40 m sequence-centroid heuristic. These are approximate route clusters, not confirmed waste sites or proof of independent evaluation locations.

The sample uses three evenly distributed frames per recent sequence, ordered by capture timestamp and image ID. Sample capture dates range from 28 October 2024 to 19 January 2026, as supplied by Mapillary. The API's 2048 thumbnail variant was downloaded; source JPEGs are unchanged. `manifest.json` records source links, contributors, positions and dates; `review-notes.json` records each observation. Contact sheets are inspection aids.

| Finding | Samples |
|---|---:|
| No clear target observed | 5 |
| Limited visibility | 4 |
| Uncertain scattered litter | 3 |
| Unusable: motion blur | 1 |
| Unusable: foreground occlusion | 2 |
| **Total** | **15** |

Confirmed dump-positive samples: **0**. Confirmed overflowing-bin-positive samples: **0**. These two counts are separate from the partition above. No-clear-target samples are not certified negative training labels.

## Camera and route observations

| Sequence | Recent frames before spacing | Capture date | Sample observation |
|---|---:|---|---|
| `19zTdr8e2ZFG5DWHR6yO3Q` | 117 | 2025-03-02 | Forward windshield view; haze and low sun obscure small objects |
| `cCqFRfvNk79Qd2UG1ueoEO` | 137 | 2025-03-21 | Side view; traffic, pedestrians and motion blur limit inspection |
| `doXFjK0Shsn1tHWPvOaIM2` | 146 | 2026-01-19 | Sharper forward car view; small roadside objects remain oblique |
| `LRFtDezqKn70ZpO5IEVH6j` | 26 | 2024-10-28 | Side view; two of three samples largely blocked by a rickshaw |
| `ZjeJ3SI92RMApGN71Cr0gO` | 39 | 2025-02-11 | Side view of buildings and lane entrance; small scattered litter only |

The January 2026 sequence ID also occurs in the earlier Kasba candidate. Candidate folders must not be assigned directly to independent training/test splits. Scene overlap and physical sites still need explicit review if any of this material is later used.

The sample does not establish sufficient positives for the planned 200+ labelled-image set. No clear target was found to trigger denser follow-up sampling in this round. Move to the next search lead, Poona Hospital / Two-Wheeler Bridge, before spending more download effort here. Do not relax the freshness window or class definitions. No annotation or training has started.
