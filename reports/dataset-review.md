# Public dataset review for scope decision E + A

Checked 13 September 2026, after the user chose option E (train on existing public data) combined with option A (report the Mapillary positive-scarcity result as a finding). See the [round 8 comparison](coverage/round-8-comparison.md) for why the Pune corridor search ended.

**Bottom line: `roadside_dump` can be sourced from openly licensed public data, including a Pune dataset. `overflowing_bin` cannot yet. No verified, openly licensed bounding-box dataset for overflowing bins was found, and both viable routes need a further step.**

Verification status used below:

- **Verified**: licence and counts read from the dataset's own page or API.
- **Partial**: some facts verified, others only from a paper or search listing.
- **Unverified**: the primary page was blocked or unreachable; treat the figures as leads.

## Usable candidates

| Dataset | Relevant class | Images | Annotation | Imagery | Licence | Access | Status |
|---|---|---:|---|---|---|---|---|
| [QR4Change - Urban Civic Issues: Potholes and Garbage](https://data.mendeley.com/datasets/zndzygc3p3/2) (DOI 10.17632/zndzygc3p3.2) | `roadside_dump` | 712 garbage-dump + 1,259 non-garbage | Image-level folders only; **no boxes** | Smartphone field survey in Pune (Kondhwa, Bibewadi, Swargate, Market Yard), mixed with images from open repositories and government portals | CC BY 4.0; the licence notes that third-party content inside may need further permission | Open download | Verified |
| [pLitterStreet](https://github.com/gicait/pLitter) ([Zenodo 8288500](https://doi.org/10.5281/zenodo.8288500)) | `roadside_dump` (roadside litter piles) | 13,000+ per [paper](https://arxiv.org/abs/2401.14719) | COCO-format boxes | Vehicle-mounted street cameras in Thailand, Vietnam and Sri Lanka | The arXiv record states CC BY 4.0; the GitHub repository declares none; the Zenodo record timed out on four attempts | Open (Zenodo) | Partial: confirm licence in the downloaded archive |
| [Roboflow: Waste Street View](https://universe.roboflow.com/cartodx/waste-street-view) (CartoDx) | `roadside_dump`, possibly | 2,584 | Boxes | Street view | CC BY 4.0 | Roboflow export | Partial: class list not confirmed |
| [Roboflow: Piles of garbage](https://universe.roboflow.com/naki/piles-of-garbage) (naki) | `roadside_dump` | 359 | Boxes | Not inspected | CC BY 4.0 | Roboflow export | Partial: listing describes "garbage-bottles" images; check content |
| [Roboflow: Garbage](https://universe.roboflow.com/dsoelma/garbage-clixe) (dsoelma) | Either, unconfirmed | 524 | Boxes | Not inspected | CC BY 4.0 | Roboflow export | Partial: class list not confirmed |
| [Roboflow: garbage can overflow](https://universe.roboflow.com/mariswary-deepak-4ajr0/garbage-can-overflow) (Mariswary Deepak) | `overflowing_bin` | about 2,000, 10 classes including "trash flow" | Boxes | Not inspected | CC BY 4.0 per search listing | Roboflow export | **Unverified**: page blocked by bot protection. The only openly licensed overflowing-bin box candidate found |
| [StreetView-Waste](https://streetview-waste.di.ubi.pt/) (University of Beira Interior, [WACV 2026](https://arxiv.org/abs/2511.16440)) | `overflowing_bin` | 36,478 fisheye frames; 71,170 container boxes; 5,149 overflow masks | Boxes, tracks, overflow instance masks | Side cameras on waste-collection vehicles, European city streets | Paper: CC BY 4.0 under a data licence agreement for academic research with GDPR conditions | Download links return **401 Unauthorized**; access must be requested | Partial: strongest overflow source, but gated |
| [TACO](https://github.com/pedropro/TACO) | Neither directly | 1,500 | Instance segmentation | Mostly close-up litter "in the wild" | Annotations CC BY 4.0; each image keeps its own Flickr licence | Open | Verified via [paper](https://arxiv.org/abs/2003.06975) and dataset documentation. Weak class match; optional warm-start only |
| [RoLID-11K](https://github.com/xq141839/RoLID-11K) | Neither | 11,000+ | Boxes | UK dashcam; small, sparse verge litter | Repository Apache-2.0; dataset licence to confirm | Open | Partial. Possible verge background or hard negatives only |

## Inspection results, 13 September 2026

### Roboflow metadata

Metadata comes from the Roboflow API ([summary](public-datasets/roboflow-20260913-143937.json)). **All four sets report `license=CC BY 4.0`**, which resolves the licence gap noted in the table above.

| Set | Images | Classes reported by the API | Assessment |
|---|---:|---|---|
| garbage can overflow | 1,974 | Trash flow 620, Healthy trash can 602, Close_empty 560, Open_empty 532, Open_full 508, Broken trash can 351, Close_full 273, full 193, closed 50, empty 37 | Overflowing-bin candidate. "Trash flow", "Open_full", "Close_full" and "full" must be checked visually against the class definition before mapping. Newest version 4 splits 1,961 / 11 / 2 images, so re-split for evaluation. |
| Waste Street View | 2,584 in project; versions up to 10,336 are augmented | litter 8,788 | Scattered litter only, which the class definitions exclude from `roadside_dump`. Not downloaded. |
| Piles of garbage | 359 | unnamed classes 0 (268), 2 (124), 1 (54) | Class meanings undocumented; downloaded for visual inspection. |
| Garbage (dsoelma) | 524 | empty-or-no-detect 1,285, KGO (bulky waste) 432, full 374, little-garbage 339, re-full 188, fill percentages, stray labels (`e`, `r`, "Метаинформация") and Russian-language variants | Russian container-site imagery. "re-full" may match overflowing bins and "KGO outside container" may match dumping, but labelling is inconsistent. Downloaded for visual inspection. |

### garbage can overflow: label inspection

The export is version 4 in YOLOv8 format: 1,974 images with matching label files (1,961 train, 11 valid, 2 test) and a README stating CC BY 4.0. Extraction shortened 202 overlong filenames. The export merges the API's ten classes into five: Broken trash can (292 images), Healthy trash can (440), Trash can closed (350), Trash can open (381) and **Trash over flow (882 images, 1,593 boxes)**. Counts: [label summary](public-datasets/garbage_can_overflow-labels.json).

**Provenance, from filenames.** 151 images are pre-augmented uploads (grid-mask, blur, mosaic), and 81 are stock photos (Getty Images, Depositphotos) that the uploader's CC BY 4.0 cannot relicense. The rest are generically numbered web or CCTV frames, camera timestamp series and phone photos of Iranian dumpsters. Of the 882 overflow images, 78 are stock and 38 augmented.

**A 24-image sample of "Trash over flow" shows the class is broader than `overflowing_bin`:**

- About 9 match the project definition: waste spilling out of, or heaped around, a visible bin or container.
- 6 are Chinese bin-station CCTV frames of bins full to the brim but not spilling.
- The rest are closed bins with nothing spilling, loose litter being swept, a burning roadside pile, a cardboard heap with no bin, a construction skip of rubble, or a studio product shot.
- Boxes follow no single convention: some enclose the bin, some only the spilled waste, some both.

**Assessment: usable only as a filtered and re-labelled source.** Drop augmented and stock images, review every "Trash over flow" image against the class definition, and redraw boxes to one convention in local CVAT. Expect roughly 250-350 usable overflowing-bin images, drawn from Chinese, European, Iranian and stock-style scenes rather than Indian streets. The healthy, closed and open bin images are mostly dumpster close-ups and product shots, which make weak hard negatives. The CCTV full-bin frames could serve as difficult negatives, because the definition requires visible spillage.

### Piles of garbage: label inspection

The export is version 1: 359 images (249 train, 75 valid, 35 test), stretched to 640 x 640, with a README stating CC BY 4.0. `data.yaml` names two classes, "1" and "2"; the API's "0" label does not appear in the export. Counts: [label summary](public-datasets/piles_of_garbage-labels.json).

- **Class "1", 285 images:** garbage piles, mostly ground-level phone and WhatsApp photos of South Asian roadsides, walls and courtyards. A 12-image sample holds about 7 clear piles and some small litter scatter. It also contains a bin interior, and boxes around single wrappers on grass and soil. Consecutive WhatsApp photos repeat one courtyard pile.
- **Class "2", 95 images:** plastic bottles, nearly all studio close-ups on a white background. Not relevant.

**Assessment:** a small, useful `roadside_dump` supplement after filtering. Keep class "1" images with a genuine concentrated pile, drop single-item litter boxes, and group repeated scenes before splitting. Discard class "2".

### Garbage (dsoelma): label inspection

The export is version 6: 524 images (366 train, 104 valid, 54 test) with 14 classes, including four garbled names made only of dashes, where Cyrillic was lost in export. Extraction shortened 1,048 overlong filenames. Counts: [label summary](public-datasets/garbage_dsoelma-labels.json).

- **One physical site.** Every sampled frame is the same roadside container enclosure. The burned-in overlay reads "рп. Маркова, Сергиев Посад, на въезде на ул. Тенистая" with GPS near 52.24 N, 104.24 E (Irkutsk region, Russia). Collection-truck crews photographed it between June 2021 and October 2022.
- **Personal data in the overlay.** It names individual crew members and shows vehicle plates. Crop or exclude it from anything published.
- **"full" and "re-full"** boxes often surround bins whose contents are not visible, or tiny distant bins. Only a few frames show waste heaped above the rim or spilling out.
- **"KGO" (bulky waste)** covers timber, branches, a stove and boards beside or inside skips. That is mostly garden or construction material, which the `roadside_dump` definition excludes.

**Assessment: exclude from training.** A single site adds no location diversity, the labels do not match the project classes, and the overlay carries personal data. At most, a few frames could serve as difficult negatives (full-but-not-spilling bins, bulky waste) after cropping the overlay.

### QR4Change garbage subset

Inventory: [qr4change_garbage-inventory.json](public-datasets/qr4change_garbage-inventory.json).

- **Dump folder (`garbage/yes`)**: 713 files, of which 708 are JPEGs and 5 are MP4 videos. One exact duplicate pair (IMG 709 and IMG 710) leaves **707 unique images**. All are phone photos of at least 960 px, median 3000 x 4000 portrait, consistent with the Pune field survey.
- **Two contact-sheet samples, 52 distinct images**: about 27 clear roadside dumps (52%); 17 borderline or hard-negative scenes, including sparse litter, garden waste, construction rubble and soil, a vendor stall and a collection handcart; and 8 unusable frames with motion blur, rider occlusion or an indoor scene. Extrapolated, **roughly 330-410 clear dump images**, before near-duplicate grouping.
- **Burst capture, not independent sites.** 694 of the 708 JPEGs carry EXIF capture times, and none carry GPS. 610 were taken on 28 August 2025 between 14:42 and 15:46, with a median gap of one second between frames. The rest come from 27 and 29 July and 3 and 17 August 2025. Splitting wherever consecutive frames are more than 10 seconds apart gives 58 timed segments plus 14 untimed images.
- **Segment review**, using the middle frame of each segment: about 31 segments show a clear roadside dump; 16 show only sparse litter, garden waste or soil; and 9 are unusable or off-target (an indoor bucket, a handcart, motion blur, shopfronts, a puddle). Three consecutive 3 August segments, 15 photos, show one hanging street bin spilling onto the ground: a single `overflowing_bin` site. Adjacent segments may show the same site and long segments may cover several, so the **distinct dump-site count is an estimate of roughly 25-35**.
- **Split unit**: use capture-time segments, merged where photos are visually near-identical, as the equivalent of Mapillary sequences. `Group-NearDuplicates.ps1` links only time-adjacent photos for this reason; linking every pair inside a time window chained 579 of the burst photos into one group. With a 10-second adjacent-time rule plus visual near-duplicates (dHash distance 10 or less), the 708 JPEGs form **66 split groups**, 21 of them single photos, the largest holding 83 ([grouping](public-datasets/qr4change_dumps-groups.json)). Groups are a leakage-safe split unit, not a site count.
- IMG 7 shows a tipped, spilling street bin: an `overflowing_bin` example, not a `roadside_dump`.
- **Non-garbage folder (`garbage/no`)**: 1,259 images, 3 unreadable, 482 under 640 px on the short side, and 9 exact duplicate pairs. The sample is mostly unrelated web imagery (a pet, textures, a news frame), plus green kerbside containers with Uruguayan signage that appear to come from the Google Street View-derived Montevideo dataset. **Exclude this folder entirely** from training and negatives, for both licence risk and relevance. Negatives will come from the Mapillary hard negatives and the empty or healthy bin classes of other sets.

## Excluded

| Dataset | Reason |
|---|---|
| [Clean dirty containers in Montevideo](https://www.kaggle.com/datasets/rodrigolaguna/clean-dirty-containers-in-montevideo) | Built from Google Street View ([preprocessing repository](https://github.com/rola93/clean-dirty-preprocess-baseline)); Google's terms bar using Maps content to train or validate ML models (blueprint section 4). Image-level labels only. |
| [GINI / SpotGarbage](https://github.com/spotgarbage/spotgarbage-GINI) | Web-crawled images with no licence file; the maintainer must be contacted. |
| [EcoDetect-YOLO dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC11280945/) | Chinese surveillance footage; available only on request from the authors. |
| [Sangareddy Garbage Vulnerable Point dataset](https://arxiv.org/html/2511.07325) | Promised but not released; fixed CCTV viewpoint. |
| [UrbanDumpSight](https://www.scidb.cn/en/detail?dataSetId=422fc2020c7c405288bdacb792c61d8d) | Image source and licence could not be read from the SciDB page; not verifiable. |
| Garbage Bin Status (GBS), [Smart Cities 2025](https://doi.org/10.3390/smartcities8020071) | About half of its 16,771 images are Stable Diffusion synthetic; no public download found. |
| [Unidata Outdoor Garbage](https://unidata.pro/datasets/outdoor-garbage/) | Commercial dataset. |

## What this means for the two classes

*Updated 13 September 2026 after all inspections.*

**`roadside_dump` has usable sources.** QR4Change supplies 707 unique Pune phone photos in 66 split groups, with boxes still to draw. Roboflow "Piles of garbage" class "1" adds 285 South Asian pile photos with pre-filled boxes to correct. pLitterStreet remains an unchecked option.

**`overflowing_bin` rests on one filtered source.** Of the Roboflow "garbage can overflow" images, 766 "Trash over flow" images remain after removing stock and pre-augmented copies. That label is broader than the project definition, so expect roughly 250-350 to survive review. QR4Change adds one Pune site, 15 photos. The dsoelma set was rejected, and StreetView-Waste was not requested. The domain gap to Pune community bins remains and should be reported with the results.

## Class mapping and licensing rules

- Map each source class to the project classes in a written table before training: for example, QR4Change "garbage dump" to `roadside_dump`, and Roboflow "trash flow" or StreetView-Waste overflow masks to `overflowing_bin`. Keep sources whose labels do not match the definitions out of training rather than relabelling them loosely.
- Keep a provenance column per image (dataset, original URL or ID, licence). For QR4Change, flag images that cannot be tied to the Pune field survey, since the licence warns about third-party content.
- CC BY 4.0 sources are compatible with the CC BY-SA 4.0 Mapillary-derived material. Keep one attribution file per source, and never mix in Google Street View-derived data.

## Evaluation on Pune (option A)

- Report detector metrics on held-out splits of the public data, per source and **source-disjoint** where possible, so the number is not inflated by near-duplicate images.
- Use the reviewed Pune Mapillary imagery as a **diagnostic set**, not a benchmark: the Aundh bridge-railing dump (8 frames, one split group) as the only positive, and the hard negatives recorded across rounds 1-8 as a false-positive test.
- Run the geometry pipeline on the Aundh dump frames as a worked localisation case study. One site cannot support the 80%-within-15-m statistic.

## Next steps

Done: QR4Change and three Roboflow sets downloaded and inspected, and Waste Street View rejected on its class list alone. Split groups were built for every source; the Roboflow sets use dHash distance 5 or less, because distance 10 chained 660 overflow images into one group. The provenance manifest, Label Studio import files and a tested geolocation module are in place:

- [Labelling manifest and workflow](labelling/README.md): 1,758 images queued (977 `roadside_dump`, 781 `overflowing_bin`) with 1,722 pre-filled boxes, plus 33 Pune diagnostic images kept in a separate project.
- [Geolocation worked example](geolocation/aundh-worked-example.md): the Aundh dump located from 4 views, stable to within 2.9 m under a 13-degree heading shift.

Remaining:

1. **User:** label in Label Studio until each class has about 300-400 kept images spread across split groups.
2. Convert the Label Studio JSON export into a group-disjoint YOLO train, validation and test split, with class balance and hard-negative counts recorded.
3. Train YOLOv8n on Colab T4; report per-source metrics and run the Pune diagnostic set.
4. Check the Aundh site estimate against a remote reference such as the OpenStreetMap railing line.
5. Optional: check pLitterStreet's licence and piles if `roadside_dump` needs more variety.
6. StreetView-Waste: not requested. Mapillary serves as the street-level test imagery but does not replace an overflow training source.

Both scripts read settings from `config/public-datasets.json` and write metadata to `reports/public-datasets/`; images stay under `data/`, which is excluded from version control. The Roboflow script never logs or saves the API key or signed export links.
