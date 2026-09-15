# Area B visual review - 12 September 2026

**Plan update:** the user subsequently replaced the proposed PCMC Area A follow-up with [the Pune search plan](../../../PUNE_SEARCH_PLAN.md). The original review findings below are retained as historical evidence; no PCMC corridor remains the active selection.

**Decision: do not approve Area B as the sole training corridor yet.** Metadata availability passed, but this sample did not establish suitable positive examples for either project class. Keep the downloaded material for image-processing trials and potential negative examples. Next, inspect Area A using the same sampling method; if it also lacks positive examples, search additional existing PCMC imagery. No field collection is requested.

## Sample and evidence

- Reviewed all 27 downloaded images: three from each of nine sequences, 24 spherical panoramas and three perspective frames.
- Within each sequence, sort by capture timestamp and image ID; select frames near one-sixth, one-half and five-sixths of its image list within Area B. This is deterministic sampling, not a statistically representative estimate of waste prevalence.
- Capture dates returned in metadata span 20 February 2025, 19 September 2025 and 19 January 2026. These are platform metadata, not independently verified dates.
- Downloaded the API's 2048 thumbnail variant. Each source JPEG remains unchanged. Contact sheets are mechanical inspection aids, not training images.
- The complete image-by-image observations are in `review-notes.json`; sequence, date, camera position, contributor and source links are in `manifest.json`.
- Open [the local gallery](index.html) to browse each image alongside the review notes.

## Findings

| Finding | Images |
|---|---:|
| Clear roadside dump identified | 0 |
| Clear overflowing bin identified | 0 |
| Potential difficult negative examples | 4 |
| Other images with no clear target observed | 22 |
| Image specifically flagged for limited visibility | 1 |

The last three rows partition the 27-image review. No-clear-target observations are not certified clean labels. Distant, shaded or obstructed objects may not be resolvable at this review size. This review does not establish that no waste exists in Area B.

Useful difficult negative candidates:

- `512994395180911`: produce stall with baskets, sacks and goods on the pavement.
- `1341345344412152`: stacked paving blocks and soil during pavement works.
- `765882853222897`: barricaded median work with soil and concrete pieces.
- `1804864013749227`: soil piles next to stacked concrete pipes.

These resemble patterns that a waste detector might wrongly flag, but their visible context indicates goods or construction activity. The green bin in `466116569800826` does not show visible overflow. Do not label any bin as overflowing merely because it is present.

## Quality and geometry implications

- Most visible roads and pavements are maintained residential/commercial streets. Leaves, isolated litter, parked vehicles and vendors appear frequently. The sampled frames did not reveal an obvious open dump or nullah-bank dumping scene.
- The 360-degree images provide side views, but a large part of each frame is sky or the capture vehicle. Flags, vehicles and pedestrians obstruct some views. Glare and deep tree shadows reduce detail in particular directions.
- The three perspective frames show hazy/smudged areas and vehicle foreground. `662255733592024` has particularly dark roadside regions; exclude ambiguous regions from negative labelling unless closer inspection resolves them.
- Multiple sequences revisit recognizable junctions and roads. Sequence count must not be treated as a count of independent locations; physical-site overlap needs review before dataset splitting.
- A 2048-pixel panorama contains only about 512 horizontal source pixels per 90-degree sector. Simply enlarging a crop cannot recover missing detail. Test original-resolution imagery and a recorded spherical-to-perspective transform before fixing the annotation resolution.
- The heading discrepancies identified in the coverage report remain unresolved. Image content review does not validate world bearings or geolocation.

## What is complete and what remains

The sample download, all 27 visual inspections, source manifest, contact sheets, review notes and local gallery are complete. All downloads succeeded and all source images decoded successfully during contact-sheet creation. The gallery builder checks one review note and one local source image for each manifest entry.

Full annotation and training remain on hold pending a corridor with enough clear, distinct waste scenes. Keep the original two-class definitions and minimum dataset targets. Do not relabel construction piles, scattered leaves or market goods to fill a positive-image quota.
