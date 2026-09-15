# GeoClean AI — Mapillary Street-Level Method V2 Blueprint

**Version** 2.1 · Pune Study-Area Revision
**Prepared** 12 September 2026
**Owner** Vineet · PCET's Pimpri Chinchwad University
**Status** Scope decision E + A: public-dataset training, Pune imagery as diagnostic set; data sourcing in progress

**Scope decision, 13 September 2026:** Pune screening rounds 1-8 covered all ten queue entries. No corridor is approved: across 325 individually reviewed images the searched imagery holds one confirmed roadside-dump site (Aundh, eight consecutive frames) and zero overflowing bins. See the [round 8 comparison](reports/coverage/round-8-comparison.md). The user chose **E + A**: train on existing, openly licensed public datasets, and report Mapillary positive scarcity as a project finding. Candidate sources, licences and the unresolved `overflowing_bin` gap are in the [public dataset review](reports/dataset-review.md). The decision and what it changes are recorded in [PUNE_SEARCH_PLAN.md](PUNE_SEARCH_PLAN.md#scope-decision---e--a-13-september-2026). **Sections below that assume Pune Mapillary positives for training, the 15-site target or Pune mAP are superseded where they conflict with that decision.**

**Major change:** Mapillary street-level waste detection now targets a selected Pune corridor from the user's shortlist. The PCMC Area B preference and planned Area A follow-up are retired. Use [PUNE_SEARCH_PLAN.md](PUNE_SEARCH_PLAN.md) for the current search order and selection process. Existing PCMC results remain historical evidence.

**Confirmed working decisions:** fresh build, four-week prototype target, local Label Studio (replacing local CVAT on 13 September 2026, because CVAT needs Docker and this machine has 7.9 GB RAM), existing imagery only, and remote location evaluation. No self-capture or field survey is part of the active plan. These decisions supersede conflicting legacy examples below.

---

## 1. Executive Summary

GeoClean AI v1 detected waste dumps from Esri World Imagery satellite tiles at z18 (~0.57 m/px). At that resolution a 3 m dump spans roughly five pixels — below the reliable detection floor for the object class we care about.

**v2 replaces the sensor.** Detection moves to ground-level crowdsourced street imagery from Mapillary. Build the geospatial backend, API layer and dashboard from scratch; no v1 application is present in this workspace. Satellite imagery is removed entirely; the basemap uses OpenStreetMap. Verify applicable imagery and software terms before dataset publication.

**One-line justification for review:** *Satellite imagery cannot resolve the object class the system is designed to detect, so the project moved to a sensing modality that can.*

### Headline change

| | v1 | v2 |
|---|---|---|
| Source | Esri World Imagery, z18 | Mapillary street-level |
| Resolution | ~0.57 m/px, nadir | Variable with camera, image size, object distance and projection |
| Basemap | Esri | OpenStreetMap |
| Core output | Dump polygon + area (m²) | Point location + class + view count |
| Core technical problem | Small-object detection | Detection **plus** monocular geolocation |
| Coverage model | Continuous area | Road network only |

---

## 2. Scope

### In scope

- One final Pune road corridor selected from [the Pune search queue](PUNE_SEARCH_PLAN.md), starting with Bhavani Peth-Nana Peth and the Kasba-Mangalwar-Raviwar belt
- Two detection classes: `roadside_dump`, `overflowing_bin`
- Ray-intersection geolocation from multi-view sequences
- PostGIS-backed site registry with multi-view confidence
- React + Leaflet dashboard on OSM basemap with MapillaryJS inspection panel
- Written report with metrics, limitations and reproducibility notes

### Explicitly out of scope

| Deferred | Reason |
|---|---|
| Full 5×5 km AOI | Prototype proves method, not coverage |
| 4-class taxonomy (construction debris, scattered litter) | Doubles annotation cost, adds no proof |
| Self-capture campaign and field survey | Excluded by user preference; use existing Mapillary imagery |
| Area / volume estimation | Not recoverable from monocular ground imagery at this stage |
| Moshi before/after temporal study | Depended on satellite archive; formally retired |
| Live inference endpoint | Batch-offline design, see §4 |
| Mobile app, citizen reporting, municipal integration | Future work section of report |

### Retired from v1 — communicate to guide before next review

The Moshi Phase 2 collapse study (Wayback before/after analysis) has no street-level equivalent and is cancelled. This was a genuine contribution and its loss should be stated openly, not discovered by an examiner. The replacement contribution is the geolocation method (§5.5).

---

## 3. Architecture

```
                    ┌──────────────────────────────┐
   OFFLINE          │   Mapillary API v4           │
   (one-time,       │   /images  ·  /tiles         │
    Colab + local)  └───────────┬──────────────────┘
                                │ ingest.py
                                ▼
                    ┌──────────────────────────────┐
                    │  Local corpus  +  Postgres   │
                    │  JPEGs         mapillary_    │
                    │  (EXIF GPS)    images        │
                    └───────────┬──────────────────┘
                                │ subsample, dedupe
                                ▼
                    ┌──────────────────────────────┐
                    │  Roboflow / CVAT annotation  │
                    │  → YOLO format, seq-split    │
                    └───────────┬──────────────────┘
                                │
                                ▼
                    ┌──────────────────────────────┐
                    │  TACO pretrain → YOLOv8n     │
                    │  fine-tune (Colab T4)        │
                    └───────────┬──────────────────┘
                                │ batch inference
                                ▼
                    ┌──────────────────────────────┐
                    │  geolocate.py                │
                    │  bearing → ray → intersect   │
                    │  (EPSG:32643, metres)        │
                    └───────────┬──────────────────┘
                                │
        ════════════════════════▼════════════════════════
                    ┌──────────────────────────────┐
   ONLINE           │  PostGIS: waste_sites        │
   (serving only)   │           detections         │
                    └───────────┬──────────────────┘
                                │
                    ┌───────────▼──────────────────┐
                    │  FastAPI  →  GeoJSON         │
                    └───────────┬──────────────────┘
                                │      ┌─────────────────┐
                    ┌───────────▼──────┴───┐  fallback   │
                    │  React + Leaflet     │◄── sites.geojson (static)
                    │  OSM basemap         │
                    │  MapillaryJS panel   │
                    └──────────────────────┘
```

**Design principle — zero marginal cost.** All GPU work happens offline, once. Production serves precomputed rows. There is no inference endpoint, no GPU bill, no usage meter, and nothing that can generate a charge.

---

## 4. Tech Stack

### Locked

| Layer | Component | Licence / Tier | Notes |
|---|---|---|---|
| Imagery | Mapillary API v4 | CC BY-SA 4.0, free | ~50k req/day; bbox < 0.01° |
| SDK | `mapillary-python-sdk` | MIT | Handles bbox tiling above the cap |
| Geometry | Shapely, pyproj | BSD | **All math in EPSG:32643** |
| DB | PostgreSQL + PostGIS | Supabase free | Extension toggle in dashboard |
| Annotation | Local Label Studio | Apache-2.0 | Replaced local CVAT, 13 Sep 2026; see [labelling workflow](reports/labelling/README.md) |
| Pretrain | TACO dataset | CC BY 4.0 | ~1,500 ground-level litter images |
| Model | YOLOv8n (Ultralytics) | **AGPL-3.0** | Licence implication noted in §8 |
| Training | Google Colab | Free T4 | 100 epochs @ 640px |
| Tracking | Weights & Biases | Free tier | One flag; produces report figures |
| API | FastAPI + asyncpg | MIT | Fresh build |
| Frontend | React + Leaflet + MapillaryJS | BSD / MIT | Fresh build on OSM |
| Basemap | OpenStreetMap tiles | ODbL | Attribution only |
| Deploy | Vercel + Render/HF Spaces | Free | Plus static fallback, §6.3 |

### Annotation tool decision

- **Roboflow free** — faster, assisted labelling, direct YOLO export. Workspace is public, which incidentally satisfies ShareAlike.
- **CVAT / Label Studio** — local, no visibility constraint, slower setup.

*Decision: use local Label Studio, installed with pip in `.venv`. It replaced local CVAT on 13 September 2026 because CVAT needs Docker, which is not installed, and this machine has 7.9 GB RAM. Hosted labelling is not the active workflow.*

### Deliberately not changed

| Temptation | Verdict |
|---|---|
| Swap YOLOv8n for an Apache-2.0 model | No. Costs a week, buys a licence clause. Document AGPL instead. |
| Swap Leaflet for MapLibre GL | No. MapLibre is the better vector-tile fit, but v1 Leaflet code works. Revisit only if the coverage layer misbehaves. |
| Google Maps basemap | **Blocked.** ToS §3.2.3(e) bars Google Maps Content displayed with or near a non-Google map — Mapillary coverage tiles on a Google basemap is that exact pattern. Also requires a live payment method. |
| Google Street View imagery | **Blocked.** ToS §3.2.3(c) bars use of Maps Content to train, test, validate or fine-tune ML models. |

---

## 5. Implementation Detail

### 5.1 Phase 0 — Pune coverage and positive-example validation *(week 1 gate)*

**This gates everything. Do not write pipeline code first.**

Resolve named Pune roads and bounds using the active search plan, then inspect Mapillary coverage and capture dates. Do not run the existing coverage script's PCMC rectangles as if they were Pune candidates.

Record for each candidate corridor:

- Sequence count within AOI
- Capture date distribution (reject imagery older than ~2 years)
- Camera type mix (360° panoramas vs forward-facing)
- Whether coverage reaches vacant plots and nullah banks or stops at arterial roads

**Exit criteria — all must hold:**

- [ ] ≥ 300 metadata-eligible images after filtering to the last 24 months and approximately five-metre spacing
- [ ] ≥ 3 distinct **physical locations**, measured by merging sequence centroids within 40 m — not ≥ 3 sequence IDs. Pune round 1 returned 23 recent sequence IDs across only 13 locations, with three IDs at one identical coordinate, so a sequence count cannot establish a leakage-free split
- [ ] Camera aim and ground coverage checked per sequence before dense sampling. Crowdsourced coverage mixes car dashcams, upward-aimed facade surveys, dusk side-window rides, handheld walks and low two-wheeler mounts; sequences that do not frame the roadside surface cannot contribute training data whatever their frame count
- [ ] Sample review establishes useful image quality and clear positives for both project classes; follow-up frames support the planned annotation counts

**If failed:** continue through the Pune search queue under C1 (§7). A metadata pass without positive waste examples does not approve a training corridor.

---

### 5.2 Phase 1 — Ingest

1. Tile AOI into 0.01° cells (~1.1 km; roughly 25 cells for 5×5 km)
2. Per cell, query `/images` for: `id`, `geometry`, `compass_angle`, `captured_at`, `camera_type`, `thumb_2048_url`
3. Download JPEGs at 2048 px; write GPS to EXIF so files are self-contained
4. Insert rows into `mapillary_images`
5. Subsample to ~1 frame per 5 m of travel — sequences fire every few metres

**Exit criteria:** corpus on disk, row count matches file count, every row has non-null `compass_angle`.

---

### 5.3 Phase 2 — Annotation *(the bottleneck — budget generously)*

Target set:

| Group | Count | Purpose |
|---|---|---|
| `roadside_dump` positives | 100–150 | Primary class |
| `overflowing_bin` positives | 50–80 | Secondary class |
| **Hard negatives** | **50–80** | **Critical — see below** |

**Hard negatives are not optional.** Indian street scenes contain many objects a naive waste detector will flag: construction sand piles, brick stacks, market stall goods, roadside scrap dealers, stacked sacks, rubble from ongoing works. Deliberately label images containing these **and no waste**. This single decision will move your false-positive rate more than any architecture change.

**Split by sequence, never by image.** Consecutive frames are near-identical; image-level splitting leaks the same dump across train and validation and produces a mAP number that is meaningless. Assign whole sequences to train or val.

**Exit criteria:** ≥ 200 labelled images, sequence-disjoint split recorded in a manifest file, class balance documented.

---

### 5.4 Phase 3 — Training

1. Pretrain / warm-start on TACO
2. Fine-tune YOLOv8n: 100 epochs, 640 px, default augmentation
3. Log to W&B — loss curves, PR curves, per-class mAP become report figures directly
4. Record mAP@50, mAP@50-95, precision, recall per class
5. Run batch inference over the full corpus, write to `detections`

**Exit criteria:** mAP@50 ≥ 0.55 on the sequence-held-out validation set. Below that, return to Phase 2 and add data rather than tuning hyperparameters.

---

### 5.5 Phase 4 — Geolocation *(the technical contribution)*

Satellite gave area estimation as the hard technical content. This replaces it.

**Problem:** a detection exists in image space. The dump is not at the camera's GPS position.

**Method:**

1. Take bbox centre, compute horizontal pixel offset from image centre
2. Convert to angular offset using camera horizontal FOV (from `camera_type`; 360° panoramas map pixel-x directly to bearing)
3. `bearing = compass_angle + angular_offset`
4. **Reproject camera position to EPSG:32643 (UTM 43N)** — all subsequent math in metres
5. Cast a ray from camera position along `bearing`, capped at ~40 m
6. Cluster rays from consecutive frames; intersect converging rays → ground position
7. Reproject result to EPSG:4326 for storage

**Why the CRS step matters:** at Pune's latitude one degree of longitude is ~105 km while one degree of latitude is ~111 km. Intersecting rays in degree space skews every bearing and lands results tens of metres off — silently, with no error raised.

**Fallback:** where only one view exists, place the site at a fixed 10 m offset along the camera heading and flag `view_count = 1` as low confidence.

**Bonus:** this solves deduplication for free. Rays that converge are one site; rays that do not are separate sites.

**Remote evaluation target:** ≥ 80% of checkable sites within 15 m of defensible remote reference positions. Record reference uncertainty, uncheckable sites and results by location method. This is approximate map alignment, not field-verified accuracy.

---

### 5.6 Phase 5 — Serve

FastAPI reads PostGIS, returns GeoJSON. React renders markers on OSM. Click a marker → MapillaryJS viewer loads that `image_id` in a side panel with the detection box overlaid.

Surface `view_count` in the popup — a site confirmed from 12 frames is real; one from a single frame is probably a false positive. This is your honesty signal and reviewers respond well to it.

---

## 6. Schema & Key Code

### 6.1 Database

```sql
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE mapillary_images (
  image_id      TEXT PRIMARY KEY,
  sequence_id   TEXT NOT NULL,
  captured_at   TIMESTAMPTZ,
  compass_angle REAL,
  camera_type   TEXT,
  geom          GEOMETRY(Point, 4326) NOT NULL
);

CREATE TABLE waste_sites (
  id          BIGSERIAL PRIMARY KEY,
  geom        GEOMETRY(Point, 4326) NOT NULL,   -- ray intersection
  class       TEXT NOT NULL,
  view_count  INT  NOT NULL DEFAULT 1,
  confidence  REAL,
  method      TEXT CHECK (method IN ('intersection','single_view_offset')),
  first_seen  TIMESTAMPTZ,
  last_seen   TIMESTAMPTZ
);

CREATE TABLE detections (
  id          BIGSERIAL PRIMARY KEY,
  image_id    TEXT   REFERENCES mapillary_images,
  class       TEXT   NOT NULL,
  confidence  REAL   NOT NULL,
  bbox        JSONB  NOT NULL,
  bearing     REAL,
  site_id     BIGINT REFERENCES waste_sites
);

CREATE INDEX ON mapillary_images USING GIST (geom);
CREATE INDEX ON waste_sites      USING GIST (geom);
CREATE INDEX ON detections (site_id);
```

### 6.2 Basemap + coverage layer

```js
const map = L.map('map').setView([18.65, 73.77], 15);

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '© OpenStreetMap contributors',
  maxZoom: 19
}).addTo(map);

// Mapillary coverage — vector tiles (MVT), needs Leaflet.VectorGrid
L.vectorGrid.protobuf(
  'https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}?access_token=' + TOKEN,
  { attribution: 'Imagery © Mapillary contributors, CC BY-SA 4.0' }
).addTo(map);
```

The coverage layer mainly shows *where you looked* — which directly supports the limitations section.

### 6.3 Demo resilience

Supabase pauses idle projects after ~7 days; Render and HF Spaces cold-start in 30–60 s. A dead demo during review is an avoidable failure.

```js
const load = async () => {
  try {
    const r = await fetch(API_URL + '/sites', { signal: AbortSignal.timeout(3000) });
    if (!r.ok) throw new Error('api');
    return await r.json();
  } catch {
    return (await fetch('/sites.geojson')).json();   // static, always up
  }
};
```

Export `sites.geojson` to the Vercel build on every data refresh. Ten lines; the demo becomes unkillable.

---

## 7. Risk Register

| ID | Risk | L | I | Mitigation | Trigger |
|---|---|---|---|---|---|
| R1 | Sparse/stale imagery or insufficient waste examples | **H** | **H** | Separate metadata and visual-content gates | Candidate fails either gate → next Pune candidate under C1 |
| R2 | Ray math done in degrees → wrong positions | M | **H** | EPSG:32643 mandated; unit test with known pair | Spot-check > 15 m error |
| R3 | Image-level split inflates mAP | M | **H** | Sequence-disjoint split in manifest | Val mAP >> visual quality |
| R4 | High FP rate on construction/market scenes | **H** | M | 50–80 hard negatives in Phase 2 | Precision < 0.6 |
| R5 | Free-tier sleep kills live demo | **H** | M | Static GeoJSON fallback (§6.3) | — |
| R6 | Annotation overruns schedule | **H** | M | Local Label Studio with pre-filled Roboflow boxes; tasks ordered one image per split group first; stop at about 300-400 kept images per class | Week 2 annotation milestone slips |
| R7 | AGPL-3.0 obligation via Ultralytics | M | L | Document in report; keep repo public | — |
| R8 | ShareAlike on derived dataset | M | L | Publish dataset CC BY-SA; intended, not a cost | — |
| R9 | Guide objects to scope pivot | M | **H** | Brief **before** next review, not during | — |

### Contingency C1 / Plan B — existing Pune imagery search

The user has replaced the PCMC fallback with the Pune shortlist. Search existing Mapillary imagery in the order recorded in [PUNE_SEARCH_PLAN.md](PUNE_SEARCH_PLAN.md). Start with Bhavani Peth-Nana Peth and the Kasba-Mangalwar-Raviwar belt, then specific SRA locations and the remaining leads.

Do not ask the user to collect field data, self-capture imagery or compile municipal reports. Keep the two classes and freshness requirements. If the shortlist is exhausted without sufficient data, record the evidence and obtain a specific scope decision before relaxing those requirements. Locality descriptions and historical reports are search leads, not labels or proof of current conditions.

---

## 8. Acceptance Criteria

**Prototype is done when all of these hold:**

- [ ] ≥ 300 usable recent Mapillary images retained after spacing, with recorded camera positions and valid headings
- [ ] ≥ 200 images annotated, sequence-disjoint split, hard negatives included
- [ ] mAP@50 ≥ 0.55 on held-out sequences
- [ ] ≥ 15 distinct `waste_sites` in PostGIS
- [ ] Remote alignment evaluated against the 80%-within-15-m target, with uncertainty and uncheckable sites reported; no field-verification claim
- [ ] Dashboard loads on OSM with markers, popups and MapillaryJS panel
- [ ] Static fallback verified by killing the API and reloading
- [ ] Attribution present: OSM (ODbL) and Mapillary (CC BY-SA 4.0)
- [ ] AGPL-3.0 dependency disclosed in README
- [ ] W&B run exported with loss, PR and per-class mAP figures

**Headline result for the presentation** — one slide, one number:

> Detected **N** candidate waste sites across **K** km of inspected Pune roads, **M** supported by ≥ 3 distinct camera positions. State the imagery capture dates.

---

## 9. Schedule

Four-week prototype target, with 20 working days for one primary builder. Corridor and positive-example discovery gate full annotation and training.

| Week | Phase | Output |
|---|---|---|
| 1 | Phases 0–1 and geometry trial | Pune corridor selected, imagery and positive-example gates passed, corpus and small location trial |
| 2 | Phases 2–3 | Local CVAT annotation, split manifest, baseline model and metrics |
| 3 | Phases 4–5 | Batch detections, location estimates, API and dashboard integration |
| 4 | Evaluation and wrap | Remote evaluation, fallback test, report, demo and two buffer days |

**Buffer:** two days within week 4. Rebaseline if usable positive-example discovery exceeds week 1; do not silently weaken the dataset gates.

**Do not parallelise Phases 0–1 with anything.** If the corridor changes, everything downstream rebuilds.

---

## 10. Build Prompts

Reusable prompts for Claude Code or an agentic IDE. Each is scoped to one module with explicit constraints, so the output does not need rewriting.

### P1 — Ingest

```
Write `ingest.py` for a geospatial waste-detection project.

Context: Mapillary API v4, access token in env var MAPILLARY_TOKEN.
AOI is a lat/lon bounding box passed as CLI args.

Requirements:
- Split the AOI into sub-cells smaller than 0.01 degrees square.
  The Mapillary API rejects larger bbox queries on /images as of Jan 2026.
- For each cell, query /images. Fields: id, geometry, compass_angle,
  captured_at, camera_type, thumb_2048_url.
- Filter out images captured more than 24 months ago.
- Subsample to approximately one frame per 5 metres along each sequence,
  using haversine distance between consecutive frames in the same sequence_id.
- Download thumb_2048_url to ./corpus/{sequence_id}/{image_id}.jpg and write
  GPS latitude/longitude into EXIF using piexif.
- Insert rows into a Postgres table `mapillary_images` (PostGIS, EPSG:4326)
  using asyncpg. Upsert on image_id.
- Respect rate limits: max 10 concurrent requests, exponential backoff on 429.
- Log per-cell counts and a final summary.

Constraints: Python 3.11, async where it helps, type hints, no pandas.
```

### P2 — Geolocation

```
Write `geolocate.py`. This converts 2D detections into ground positions.

Input: rows from `detections` joined to `mapillary_images`, giving for each
detection: bbox (normalised xyxy), image width/height, camera lat/lon,
compass_angle (degrees from north), camera_type, sequence_id, captured_at.

Algorithm:
1. Compute bbox centre x. Derive angular offset from image centre using
   horizontal FOV. For camera_type "spherical", pixel-x maps linearly to
   0-360 degrees. For "perspective", assume 90 degree HFOV unless overridden.
2. bearing = (compass_angle + angular_offset) mod 360.
3. CRITICAL: reproject camera positions from EPSG:4326 to EPSG:32643 (UTM 43N)
   with pyproj BEFORE any geometry. All ray math happens in metres.
   Reproject results back to 4326 only for storage.
4. Build a ray per detection: origin = camera position, direction = bearing,
   length = 40 m.
5. Cluster rays: group by sequence_id, then greedily group rays whose
   pairwise intersection points lie within 15 m of each other.
6. For each cluster with >= 2 rays, the site position is the centroid of
   pairwise intersection points. Set method = 'intersection'.
7. For singleton rays, place the site 10 m along the bearing.
   Set method = 'single_view_offset'.
8. Write to `waste_sites` (geom, class, view_count, confidence as mean
   detection confidence, method, first_seen, last_seen) and update
   detections.site_id.

Constraints: Shapely 2.x, pyproj, asyncpg. Include a unit test using two
synthetic cameras 20 m apart with known bearings that should intersect at a
known point — assert the result is within 1 m.
```

### P3 — Dashboard

```
Update the existing React + Leaflet dashboard for street-level detections.

Changes:
1. Replace the Esri World Imagery basemap with OpenStreetMap:
   https://tile.openstreetmap.org/{z}/{x}/{y}.png
   attribution "© OpenStreetMap contributors", maxZoom 19.
2. Add a Mapillary coverage overlay using Leaflet.VectorGrid against
   https://tiles.mapillary.com/maps/vtp/mly1_public/2/{z}/{x}/{y}
   with the access token as a query param. Attribution:
   "Imagery © Mapillary contributors, CC BY-SA 4.0". Toggleable, 0.6 opacity.
3. Render waste_sites as circle markers. Radius and opacity scale with
   view_count. Colour by class. Sites with method = 'single_view_offset'
   render with a dashed outline to signal lower confidence.
4. On marker click, open a right-hand panel with a MapillaryJS viewer
   initialised to the highest-confidence detection's image_id, with the
   detection bbox drawn as an overlay.
5. Data loading: fetch GET {API_URL}/sites with a 3 second timeout.
   On any failure, fall back to a bundled static /sites.geojson.
   This must work with the API fully offline.

Constraints: existing component structure, no new state library,
Tailwind for styling. Both attributions must be visible without interaction.
```

### P4 — Report metrics

```
Write `evaluate.py` producing report-ready outputs from a trained
YOLOv8n waste detector.

Produce:
- Per-class precision, recall, mAP@50, mAP@50-95 as a markdown table
- Confusion matrix including a background/false-positive row
- A breakdown of false positives by manually tagged scene type
  (construction, market, scrap dealer, other) read from a CSV mapping
  image_id to scene tag
- Geolocation accuracy: for a CSV of ground-truth site positions, report
  median and 90th-percentile distance error in metres, computed in EPSG:32643,
  split by method ('intersection' vs 'single_view_offset')
- Export all figures as 300 dpi PNG into ./report_figures/

Constraints: ultralytics, matplotlib only (no seaborn), every figure needs
axis labels and a caption printed to stdout for pasting into the report.
```

### Prompt guidance

- **Give the constraint that will otherwise be got wrong.** The EPSG:32643 instruction in P2 is the difference between correct and silently-wrong output.
- **State the invariant, not just the feature.** "Must work with the API fully offline" produces a real fallback; "add a fallback" produces a `catch` block that logs.
- **Ask for the test.** P2 specifies the synthetic two-camera case. Geometry code that is not tested is geometry code that is wrong.
- **One module per prompt.** Asking for the whole pipeline in one go produces code that compiles and does not work.

---

## 11. Communication

**Before the next review**, brief your guide in writing:

1. Resolution ceiling justified the sensor change — lead with the five-pixel argument
2. Moshi temporal study is retired; geolocation method replaces it as the technical contribution
3. Project title changes: *"Street-Level Waste Detection and Mapping from Crowdsourced Imagery"*
4. The implementation is a fresh build; the selected study area is now Pune, using existing imagery and remote evaluation

A pivot announced in advance reads as engineering judgement. The same pivot discovered mid-presentation reads as drift. This is the cheapest risk on the register to close.

---

## Appendix A — Licence Obligations

| Asset | Licence | Obligation |
|---|---|---|
| Mapillary imagery | CC BY-SA 4.0 | Attribute; derived dataset published under CC BY-SA |
| OpenStreetMap tiles | ODbL | Attribute "© OpenStreetMap contributors" |
| TACO dataset | CC BY 4.0 | Attribute |
| Ultralytics YOLOv8 | AGPL-3.0 | Source disclosure if distributed — keep repo public |

**Note:** Mapillary Vistas (the 25k segmentation dataset) is CC BY-NC-SA and is a *different* asset from Mapillary imagery. Not used here.

**OSM tile fair use:** acceptable for prototype and demo traffic. If this ever goes public-facing, move to CARTO or self-hosted tiles.
