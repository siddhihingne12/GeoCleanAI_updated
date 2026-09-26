# GeoCleanAI

A React + MapillaryJS website for exploring Pune panoramas and detecting visible litter with a fine-tuned YOLO26 model. The frontend and FastAPI backend deploy together to Vercel.

**Public setup preview:** https://geocleanai-pune-demo.vercel.app

## Current state

The website, service interfaces, panorama projection, ONNX inference adapter, shared cache, training notebook, evaluation scripts and automated tests are implemented. **Real Pune litter accuracy has not been measured. No trained litter model is included.** An initial 500 m check found six central panoramas; a wider 15-area sample later found 194 unique panorama records, including captures from 2025 and 2026. Twelve were visually reviewed, of which ten are usable street scenes for further labelling; see `docs/IMAGE_SURVEY.md`. A real Edge walkthrough opens a central panorama beside the map with its date and credit. Automatic litter markings remain unavailable until a trained model is installed. There are no invented detections or sample photographs.

## User journey

1. Search for a place in Pune. A single match is selected immediately; choose from the list when several places match.
2. See the selected place as a blue pin, alongside green camera locations for nearby panoramas. The place stays pinned even when no photos are available.
3. Choose **Open street view** to open the nearest panorama, or select another camera pin/photo. On mobile, the page moves to the viewer.
4. Litter detection starts automatically. Look around while all six directions are checked. Suspected litter is marked in the panorama; selecting a suggestion turns toward it and shows the corresponding evidence image.

The viewer uses a captured 360° photograph, not a live feed or a reconstructed 3D city. Selecting a new place clears the previous photo and its results. Rotating or zooming does not run detection again. Reopening a previously analysed photo uses the server's saved result when available.

### Panorama analysis API

`POST /api/analyze-panorama` accepts `{"image_id":"123"}`. The existing `POST /api/analyze` endpoint still accepts an image ID and a single camera view.

Panorama analysis downloads the source once and checks six 640px perspective views with a 100° field of view, including above and below the camera. Adjacent views overlap to provide context at their edges. Cross-view box overlap suppresses duplicate suggestions before assigning unique IDs; this is a heuristic whose real-world behaviour still needs evaluation.

The response contains `image_id`, `model_version`, `analysis_version`, `captured_at`, `cached`, `elapsed_ms`, `views` (each with `id`, camera `view` and JPEG `preview`), and `detections`. Each detection has a unique `id`, `view_id`, label, confidence, normalised box within its evidence view, and a normalised panorama `tag`. Preview boxes must be filtered by `view_id`.

Completed results are cached for 24 hours using the image ID, model checksum, confidence threshold and analysis version. Both analysis endpoints share the inference lease. Missing configuration, provider failures, busy requests and timeouts return errors rather than empty detections. No partial panorama is cached or reported as complete. A cooperative 45-second processing deadline reserves time within the configured 60-second hosting limit; live performance with real weights still needs measurement, and a single blocking inference/provider call can exceed this budget.

### Real-demo prerequisites

The 25 September follow-up found both Mapillary settings populated. The first browser value could not retrieve the tested image. After the user selected **View** under **Access Token** in the Mapillary developer dashboard, the browser value retrieved that image and a real Edge walkthrough rendered its panorama. The dashboard's **Client secret** must stay out of any `VITE_*` setting. Upstash credentials and a trained model are still absent. Official TACO annotations and all 1,500 source photographs are downloaded locally and dimension-checked; the initial grouped dataset and 48 manually labeled Pune test views are packaged for Colab. TACO capture relationships beyond the duplicate audit and source licences still need review. The local search User-Agent was configured with this project's public URL, and a real search for Shivajinagar returned two Pune matches. The application changes can be tested with fixtures, but they do not satisfy the real-demo requirements below:

- Configure `.env.local` and hosting connections. Local development can use `ALLOW_LOCAL_CACHE=1` instead of Upstash.
- Verify at least ten real panoramas across multiple Pune streets; record their dates and credits in the sample catalogue.
- Prepare reviewed training data, train/export the model, and evaluate roughly fifty separate Pune views as described below.
- Meet the user-required 85% target: precision and recall must each reach at least 0.85 on independently reviewed Pune views at box IoU 0.50; see `docs/EVALUATION.md`.
- Complete an actual search-to-marked-panorama walkthrough on desktop and mobile. Measure first-load and cached timings, and inspect alignment at seams, view boundaries, different zoom levels and fullscreen.

See `docs/EVALUATION.md` for the distinction between automated checks and pending real-world evidence.

## Run locally on Windows

Prerequisites: Node 24 and Python 3.12. Use `npm.cmd` in PowerShell if execution policy blocks `npm.ps1`.

```powershell
npm.cmd ci
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env.local # only if .env.local does not already exist
```

Set these values in `.env.local`:

| Setting | Purpose |
|---|---|
| `VITE_MAPILLARY_CLIENT_TOKEN` | Value under **Access Token** in the Mapillary developer dashboard (not **Client secret**); intentionally public in the browser viewer |
| `MAPILLARY_ACCESS_TOKEN` | Mapillary access token for server-side API requests; a client access token is recommended |
| `NOMINATIM_USER_AGENT` | Project name plus your project URL or contact, replacing the placeholder |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Upstash database REST credentials; server-only |
| `ALLOW_LOCAL_CACHE=1` | Enables a local, single-process cache when Redis is absent; ignored on Vercel |

Never put a Mapillary app secret, user token, Redis token or cloud credentials into a `VITE_*` variable. The viewer specifically needs a client access token. `.env.local` is ignored by Git and Vercel uploads.

Start the backend and frontend in separate terminals:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173. Restart the backend and frontend after changing credentials. A missing model disables scanning but does not prevent browsing configured imagery.

## Check Pune imagery before training

```powershell
.\.venv\Scripts\python.exe scripts/check_coverage.py
.\.venv\Scripts\python.exe scripts/check_coverage.py --image IMAGE_ID
```

The first command queries five Pune locations and writes `artifacts/coverage.json`. It does not crawl the city. Inspect candidate photographs for resolution, dates and visible litter. The second command downloads one panorama into `artifacts/` for review. Only after visual verification should you add its returned metadata to `public/samples.json` (omit `local_path`, `width`, `height`). Keep image credits. Aim for ten usable examples on multiple streets; if none are suitable, revisit the source-image requirement.

For a wider sample across 15 areas, run `.\.venv\Scripts\python.exe scripts/survey_pune.py`. It writes `artifacts/pune-survey.json`. See `docs/IMAGE_SURVEY.md` for reviewed candidates; the survey is not a complete coverage map and does not supply litter labels.

All twelve surveyed panoramas now have original-resolution images and capture sequence metadata locally. Their 72 perspective views are in `data/pune-review/images/`; these come from nine sequences and are not 72 independent street scenes. Dates, credits and source details are in `manifest.json`. **The exporter creates no labels.**

Run `.\.venv\Scripts\python.exe -m training.review_server` and open **http://127.0.0.1:8765** to draw litter boxes, explicitly verify clean views or skip uncertain images. Reviews persist locally with reviewer names and image checksums. See [Pune review instructions](docs/PUNE_REVIEW.md) for labeling and exporting a reviewed candidate pool before selecting training and evaluation groups. The downloader/exporter refuses to overwrite images once human reviews exist.

The app uses an explicitly bounded **Pune demo area** (73.70–74.05 E, 18.40–18.70 N), not an authoritative municipal boundary. A lookup returns up to 100 candidate photographs within 500 m. If Mapillary indicates additional results, the UI labels the list as a subset. No coverage does not mean no litter.

## Train a real litter model

The manual Pune review is complete: 18 litter views, 30 clean views and 24 skipped views. The 48 usable views (54 litter regions) are reserved entirely for evaluation at `data/pune-test-v1/`. The first training run uses the TACO split.

The upload bundle and matching notebook are ready in `artifacts/colab/`. Upload the 4.79 GB `geocleanai-colab-data-v1.zip` into `My Drive/GeoCleanAI`, then open `training/GeoCleanAI_Training.ipynb` in Google Colab with a GPU runtime. Follow [the Colab steps](docs/COLAB_RUN.md). The notebook checks the upload, trains on TACO, saves checkpoints to Drive, exports `litter.onnx`, `manifest.json`, `best.pt` and runs the separate Pune evaluation. Free GPU access is not guaranteed; actual training has not run yet.

Download the source images referenced by the official, reviewed TACO annotations. The downloader resumes existing files, checks their dimensions against the annotations and writes a failure report. It accepts only the Flickr and OpenLitterMap hosts used by this annotation file.

```powershell
.\.venv\Scripts\python.exe training/download_taco.py
```

Review `data/TACO/download-report.json` and resolve every failed image before preparing the full dataset. Follow each image's licence before sharing any source photographs or a prepared dataset. Supply `groups.json` mapping every image ID to its capture/sequence group, for example:

```json
{"0": "capture-a", "1": "capture-a", "2": "capture-b"}
```

Assign visually related frames, crops and near-duplicates to the same group. The converter also merges exact duplicates by hash. TACO batch folders can help with the initial grouping but are not proof that different batches are independent. Use at least five independent groups; more are preferable.

The current local **draft** uses batch folders as groups. A perceptual-hash audit found one identical photo spanning batches 7 and 8; the converter merged those groups. The draft split contains 999 training, 324 validation and 177 test images across 14 groups, with no group shared between splits. Capture relationships beyond close visual duplicates and per-image licences still need review. Keep the prepared folder private while source licence details are unresolved.

```powershell
.\.venv\Scripts\python.exe training/prepare_dataset.py --annotations data/TACO/annotations.json --images data/TACO --groups data/groups.json --output data/litter
```

The converter writes one `litter` class, group-separated train/validation/test sets, `splits.json` and `credits.csv`. The current Colab bundle already includes this folder. Training dependencies are in `training/requirements.txt`; keep them out of the hosting environment. Do not install PyTorch or Ultralytics in the Vercel function.

After training, copy **only `litter.onnx` and `manifest.json`** into `models/`. The service checks the manifest, class list, fixed 640px model signature and SHA-256. A generic pretrained COCO model must not be labelled as a trained litter detector.

## Evaluate on Pune

The first Pune set is reserved at `data/pune-test-v1/`, with 48 reviewed views and an image/label checksum record in `evaluation-lock.json`. An empty label file means a human checked that view and found no litter; a missing label file is an error. Do not use these images for training or threshold tuning. Twenty-four skipped views remain excluded and must be disclosed when reporting scores.

```powershell
.\.venv\Scripts\python.exe training/evaluate.py --model models/litter.onnx --dataset data/pune-test-v1 --output artifacts/pune-evaluation.json
# In an environment with training dependencies, also compare the PyTorch export:
python training/evaluate.py --model models/litter.onnx --dataset data/pune-test-v1 --pt training-output/best.pt
```

Results include precision/recall at IoU 0.5, the confidence threshold, per-image misses/false alarms and inference latency. Undefined precision/recall are recorded as null, never as perfect scores. Use `docs/EVALUATION.md` for the college report. TACO test performance is not Pune performance.

## Deploy to Vercel Hobby

1. Import this repository or run `npx vercel` from the root. Keep the Vite framework preset. `vercel.json` routes `/api/*` to FastAPI and bundles `backend/` and `models/`.
2. In Vercel project settings add the Mapillary variables, Upstash credentials, `NOMINATIM_USER_AGENT`, `MODEL_PATH=models/litter.onnx`, and `MODEL_MANIFEST_PATH=models/manifest.json`. Do not add `ALLOW_LOCAL_CACHE`; production requires shared Redis.
3. Add the verified sample catalogue and trained model files before deploying a functional AI demo. Git ignores weights by default: use CLI deployment or explicitly track only the final ONNX artifact if it fits your repository limits.
4. Deploy a preview; verify `/api/health`, actual image access and a real scan. Promote after these pass. A deployment without credentials remains a clearly labelled setup preview.

The Python runtime is pinned to 3.12. Runtime packages are pinned in `requirements.txt`; Node dependencies are locked in `package-lock.json`. The hosting configuration uses a 60-second deadline and a global inference lease. Panoramas go directly from Mapillary to its browser viewer; the API fetches the image internally and returns six small analysed-view JPEGs plus JSON, not the full panorama file. Re-measure bundle size, response size and runtime with the real trained model before deployment.

The health response indicates configuration, not a provider connectivity test or measured model accuracy. Monitor Vercel logs for path, status and duration; credentials and image URLs are not logged. Remain on Hobby and Upstash Free. On quota exhaustion show a retry/setup state and use the local backup; do not enable paid upgrades automatically.

## Tests

```powershell
npm.cmd run build
npm.cmd test
New-Item -ItemType Directory -Path artifacts -Force
.\.venv\Scripts\python.exe -m pytest -q --basetemp=artifacts/pytest-local
npm.cmd run test:e2e
```

The browser suite uses installed Microsoft Edge and starts/reuses Vite. Install Edge or change the Playwright channel for another browser. Tests mock external API responses and do not establish live Mapillary coverage. Synthetic ONNX models are generated only in temporary test folders and are never bundled or presented as actual detections. Test output and screenshots go to ignored `artifacts/` and `test-results/` folders.

## Project structure

- `src/`: React dashboard, map, viewer, results and shadcn-style components.
- `backend/`, `api/`: Python providers, projection, inference, caching and Vercel entrypoint.
- `training/`: dataset conversion, Colab notebook, training and evaluation tools.
- `scripts/`: coverage and deployment checks.
- `tests/`: geometry, API, ONNX, data-splitting and browser tests.

## Data and licences

See `docs/DATA_CREDITS.md`. MapillaryJS and the AI detector are separate: Mapillary supplies the imagery, while your trained model generates the litter suggestions. Photos are historical captures, not live feeds. Pins show camera positions. AI confidence is not a calibrated accuracy percentage. No municipal reporting or cleanup verification is implemented.
