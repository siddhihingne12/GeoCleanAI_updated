# Pune Shivajinagar - Emerson Tower screening, round 7

Checked 13 September 2026. **Metadata passes; initial and focused image review do not establish training positives. Corridor not approved.**

| Check | Result |
|---|---:|
| Unique image records | 3,519 |
| Recent metadata-eligible images, cutoff 2024-09-13 | 1,444 |
| Recent frames after approximately 5 m spacing | 1,145 |
| Recent sequences after spacing | 11 |
| Sequence-centroid clusters | 4 |
| Oldest / newest capture in the rectangle | 2019-04-10 / 2026-03-05 |
| Completed search cells | 25/25 |
| Distinct downloaded images individually reviewed | 47 |
| Confirmed roadside-dump / overflowing-bin samples | 0 / 0 |

All search cells completed without recorded failures or pagination caps. Every returned image is perspective imagery and carries camera parameters, compass information and corrected position metadata. Counts describe this rectangle only. Four centroid clusters approximate route separation; they do not establish four waste sites or independent evaluation groups.

## Location and bounds

Bounds in west/south/east/north order: `73.848,18.529,73.858,18.538`. This exploratory rectangle covers Emerson Tower and Matrix complex approaches in Wakadewadi, Patil Estate lanes, the Shivajinagar railway-station edge and nearby public roads toward COEP. It does not cover all of Shivajinagar.

Location anchors: the [Emerson Export Engineering Centre listing](https://www.bharatibiz.com/en/emerson-export-engineering-centre_3M-020-3026-7000) places the office in Emerson Tower, Matrix Complex, Old Mumbai-Pune Highway, Wakadewadi; the [mapped Emerson coordinate](https://elevation.maplogs.com/poi/emerson_export_engineering_center_emerson_tower_matrix_complex_old_mumbai_pune_hwy_beside_shopper_s_stop_wakadewadi_shivajinagar_pune_maharashtra_india.493039.html) is 18.533476, 73.8533461; [Patil Estate Lane 10](https://www.geocords.com/place/shop-no1-lane-no10-patil-estate-shivajinagar-pune-maharashtra-411005-india-11871/) is mapped at 18.5325993, 73.8542802; [Shivajinagar railway station](https://mapcarta.com/W243952358) is mapped at 18.5327, 73.84949; and the [COEP official contact page](https://www.coeptech.ac.in/about-us/) confirms the nearby Shivajinagar campus address. These sources support search placement, not surveyed boundaries or waste labels.

## Content decision

The 33-image initial sample contains 16 no-clear-target observations, eight limited-visibility frames, three hard-negative candidates, one uncertain scattered-litter frame, four unusable occlusions and one unusable-quality frame. No confirmed positive was found for either project class.

A focused review of the ambiguous sequence added 14 distinct images beyond the initial sample. Nine consecutive frames show that the apparent pile is stored material above and behind an auto-parts shop. A nearby ground pile is broken tile and masonry. Both are excluded hard negatives under the current class definition. Loose wrappers and small debris along the frontage remain scattered below the dump threshold.

The [main visual review](../../visual-review/pune-shivajinagar-emerson/review.md), [initial gallery](../../visual-review/pune-shivajinagar-emerson/index.html), [distributed follow-up](../../visual-review/pune-shivajinagar-emerson-followup/index.html) and [adjacent-frame review](../../visual-review/pune-shivajinagar-emerson-adjacent/index.html) preserve the evidence. The result does not establish that every recent image lacks waste.

## Reproduction and next step

The saved `candidate-config.json` preserves this round’s bounds. Coverage can be reproduced with `Measure-MapillaryCoverage.ps1 -CandidateConfig reports/coverage/20260913-124627/candidate-config.json`. Initial sampling used `Get-MapillaryReviewSample.ps1 -MetadataFile reports/coverage/20260913-124627/pune_shivajinagar_emerson-images.json -OutputFolder reports/visual-review/pune-shivajinagar-emerson -PerSequence 3`.

The sampler now also accepts `-SequenceId` for a single-route review and `-FocusImageId` for a consecutive temporal window around one frame. The focused check used sequence `HiPTLSkfl3vECAnycUp9Nz`, which contains 231 recent frames after the freshness filter. Use `powershell.exe -NoProfile -ExecutionPolicy Bypass -File` to invoke the scripts where needed. Freshness advances on rerun; the summary preserves this run’s cutoff.

Next queued lead: entry 9, Pashan / Aundh / Baner, starting with a compact Pashan search area. No annotation or training has started. Across all completed review work, 262 distinct sample images now have individual findings.
