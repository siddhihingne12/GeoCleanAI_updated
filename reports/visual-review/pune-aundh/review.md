# Aundh - Parihar Chowk, Bremen Chowk and Gaon approaches visual review

Reviewed 13 September 2026. **Not approved for annotation: one confirmed roadside-dump site, zero overflowing bins, in 60 distinct reviewed images.**

The initial screen took up to three evenly distributed recent frames from each of the 14 recent sequences. One sequence holds a single frame, so the sample is 40 images: 27 spherical panoramas, 9 Brown-model walking frames and 4 perspective frames, captured from 25 January 2025 to 19 May 2026. Two ambiguous frames were then checked with nine consecutive frames each. The nearest frame from each of four other recent sequences was pulled to test whether the dump persisted. Accounting for overlap, the review covers 60 distinct images. These are screening observations, not training labels.

| Initial observation | Images |
|---|---:|
| Roadside dump, confirmed positive | 1 |
| Weak accumulation, below label threshold | 1 |
| No clear target | 25 |
| Limited visibility | 6 |
| Hard-negative candidate | 4 |
| Uncertain scattered litter | 2 |
| Unusable due to camera aim | 1 |
| Total | 40 |

## Confirmed roadside dump

Panorama `765068579834233` (sequence `BEohfHsAZiWFlVXwp7Gz4N`, 17 September 2025) shows a concentrated pile of mixed household waste on the verge along the red river-bridge approach railing. The waste includes plastic bags, paper, cloth and food packaging. The camera was near 73.81158, 18.56760, heading south, at the north edge of the search rectangle beside the Pimpri Chinchwad municipal welcome arch.

In the initial sample the pile spans only about 130 px of a 2,048 px panorama. Nine consecutive frames about 3 m apart confirm it in frames 2 to 9; frames 7 and 8 give the closest, clearest views. **This is one physical site.** All eight positive frames belong to a single split group and count once toward the 15-site target.

Four recent passes from other dates came within 5 to 12 m of the same point (14 February 2025 twice, 5 May 2025, and six minutes later on 17 September 2025). None shows the pile, but each looks along the bridge, faces the river railing, or was captured at dawn. Persistence is therefore **inconclusive**, not disproven.

## Other findings

- Two bags lie at the base of a public bin on a footpath (`926449619697396`), but the bin is not visibly overflowing. Recorded as weak accumulation below the label threshold.
- A tarp-covered bundle beside a shed (`1387747582372489`) looked ambiguous. Nine consecutive frames show tied bamboo or straw material under tarps, so it is stored goods and a hard negative. Five of those nine frames are motion-blurred.
- Other hard negatives are a flag vendor's tarps and crate, an ordinary public bin that is not overflowing, and a closed orange metal box outside a workshop.
- One frame (`1477396800639862`) is an indoor ice-cream-parlour photograph mis-geolocated into the street layer.

## Capture population

The 14 recent sequences come from only eight capture days. Roof-mounted 360-degree cameras account for 27 of the 40 samples and repeatedly cover the same arched boulevard and river bridge at the north edge. A January 2025 walk around Parihar Chowk supplies the footpath views. One sequence was shot at dawn, and a May 2025 phone sequence was taken through a side window with heavy motion blur. The nine centroid clusters therefore overstate independent street coverage.

Evidence: [initial gallery](index.html), [per-image notes](review-notes.json), [manifest](manifest.json), [bridge adjacent frames](../pune-aundh-adjacent-bridge/index.html), [tarp adjacent frames](../pune-aundh-adjacent-tarp/index.html), persistence checks ([urjF](../pune-aundh-dump-persistence/urjF-2025-02-14/index.html), [MzO7](../pune-aundh-dump-persistence/MzO7-2025-02-14/index.html), [Le2T](../pune-aundh-dump-persistence/Le2T-2025-05-05/index.html), [wONZ](../pune-aundh-dump-persistence/wONZ-2025-09-17/index.html)), and [coverage decision](../../coverage/20260913-131200/coverage-decision.md).
