# Evaluation record

## Local implementation evidence — 25 September 2026

- User journey implemented: search, distinct place pin, nearest-photo action, automatic six-view analysis, panorama markers, evidence selection and mobile scrolling.
- Production frontend build and the 2 frontend geometry tests passed.
- 39 Python tests verified, including whole-sphere coverage, overlap suppression, one source download, six-view inference, cache reuse/invalidation, shared concurrency, failure handling, processing deadlines and compatibility with the original single-view API. The final compatibility assertion was corrected to compare JSON arrays with JSON arrays; all 14 panorama tests passed on the targeted rerun, alongside the 25 existing passing tests.
- 14 Edge browser tests passed. The added integration tests cover automatic detection, results arriving before the viewer loads, marker/evidence selection, fullscreen, photo navigation, stale search/photo events/results, retries, unavailable-model states and mobile scrolling.
- Browser integration tests substitute a clearly labelled viewer fixture and API results. They verify application behaviour, not Mapillary alignment or litter recognition. Fixture screenshots are `artifacts/panorama-test-desktop.png` and `artifacts/panorama-test-mobile.png`; they must not be presented as real detections.
- Local search identity configured with the project's public URL. A real Nominatim search for Shivajinagar returned two matches in Pune. The network sandbox initially blocked the request; a read-only request outside it succeeded.
- At the initial implementation check, no Mapillary tokens, Upstash credentials, trained model or reviewed local training dataset were available. Local caching remains available for development. After that check, the user supplied two Mapillary values; see the live follow-up below. Training, independent Pune evaluation, real marker alignment and live model timings remain blocked on the model and data inputs.
- These changes have not been deployed to the public preview.

## Live follow-up — 25 September 2026

- The Mapillary settings are populated. The backend `/api/health` reports `mapillary: true`; it still reports `model: false`.
- Real Mapillary queries found six unique panoramas near central Pune, all from the same contributor on 27 January 2019. Four other initial locations and nine additional named areas had no panorama within 500 m. These checks show very limited candidate coverage; they do not establish a citywide count.
- One central panorama was downloaded at 3840×1920 and visually inspected. It is a usable 360° photograph. Its litter content has not been labelled or evaluated.
- An initial real Edge walkthrough reached the location map and photo list, but MapillaryJS failed to open the photo. The first browser value returned an empty `data` array for `images?image_ids=...`, while the server value returned the image record. The user then selected **Access Token** (separate from **Client secret**) in the Mapillary developer dashboard for the browser setting. With that value, the Graph photo lookup returned HTTP 200 and the image. A later Edge walkthrough with network access rendered the panorama beside the map; the viewer had no error, no loading overlay and one canvas. Its capture date and contributor credit were visible in `artifacts/live-mapillary.png`. An earlier browser run inside the network sandbox could not fetch image tiles; this was a network restriction rather than a credential failure.
- This first narrow search did not meet the ten-image presentation target; the wider follow-up below found more candidates. Positive litter labels and a trained model remain necessary for the working demo.

## Wider imagery and dataset follow-up — 25 September 2026

- A 1.5 km survey of 15 sample areas found 194 unique panorama records. The Aundh response reached the 100-image API limit, and four area requests failed; this is not a complete Pune count. Of the records found, 166 are captures from 2025–2026 in the northwest sampled areas and 28 are older central captures. See `docs/IMAGE_SURVEY.md`.
- Twelve panorama thumbnails from several sequences were visually reviewed, with dates and contributors recorded. Ten are usable street scenes for further labelling, but clean/litter labels have not been verified. Most recent wide-road scenes have no clearly visible litter at thumbnail scale; at least one older street scene has apparent roadside waste requiring original-resolution review.
- Official TACO `annotations.json` was downloaded into ignored local `data/TACO/` and contains 1,500 images and 4,784 litter annotations. All 1,500 source photos were downloaded and dimension-checked; `download-report.json` records zero failures. EXIF rotation was applied where needed to match the reviewed boxes. Image licence checks, final capture-group review, prepared training splits and Pune test labels are still pending. No model was trained and the 85% acceptance target is still unmeasured.
- The twelve surveyed panoramas were projected into 72 local annotation candidates using the same six fixed views as the service. Initially only two original panoramas were available; the later preparation fetched originals and capture metadata for all twelve. All 72 current views come from originals across nine capture sequences. No human labels have been supplied, so none is yet a verified clean or litter-positive evaluation view.
- A 256-bit perceptual-hash audit found one near-duplicate pair across TACO batches 7 and 8. The two files have identical bytes; the dataset converter merges those batch groups before splitting. Batch grouping is conservative, but distant or edited related captures can escape perceptual matching and still need review before claiming an independent TACO score.
- A draft one-class YOLO dataset was created locally at `data/litter/`: 999 train, 324 validation and 177 test images. All 1,500 images have corresponding label files; no group appears in more than one split. This prepares input for Colab training, but the split remains provisional until capture relationships and source licences are reviewed. It is not a Pune evaluation set.
- A local human review page was added at port 8765. It saves normalized boxes, reviewer, notes, timestamp and image checksum, requires an explicit clean decision, rejects stale edits and exports only reviewed original-source views. Seven targeted Python tests passed, including existing training split tests. A standalone Edge browser check passed for drawing, saving, reopening, clean/skip decisions, normalized coordinates and mobile layout using temporary fixtures. A read-only live browser check rendered the first real image and confirmed 0 of 72 reviewed; tests did not create real human labels.
- After the user reported blur, inspection found that the review page enlarged 640px detector crops. The reviewer now defaults to 1280px or 1920px projections taken directly from the original panorama, offers a 640px comparison and enlarges images at their native pixel size. The original detector images and normalized labels are preserved. Six reviewer API tests and the standalone browser check passed. Source blur and small-object information lost by the 640px detector input remain limits to measure.

## Previous hosted evidence — 19 September 2026

- Public setup preview: https://geocleanai-pune-demo.vercel.app, checked 19 September 2026.
- Production frontend build: passed with React 19.3, Vite 8.3 and TypeScript 7.
- Automated checks: 25 Python tests, 2 frontend geometry tests and 5 Edge browser tests passed. These cover geometry, validation, provider failures, cache ownership, test-only ONNX execution, group-separated data and browser state transitions.
- Real map tile rendering and bundled map worker: verified in desktop Edge; no browser errors in the hosted smoke check. Mobile layout was checked at 390px width.
- Hosted API: `/api/health` returns HTTP 200 with `setup_required`; `/api/analyze` returns HTTP 503 with `model_not_ready` when weights are missing. No fake detections are returned.
- Vercel Python runtime: 3.12. The dependency bundle was reported as 297.98 MB before Vercel optimization, without trained weights. Re-measure after adding a model.
- Real Mapillary Pune panorama availability: **not yet verified**; requires the user's client token.
- Fine-tuned litter weights: **not yet trained or supplied**.
- Pune precision and recall: **not measured**.
- Live street-view marker alignment: **not yet verified**. Mathematical projection tests are not a substitute for checking real imagery.
- Vercel cold/repeat inference latency with a trained model: **not measured**.

Do not replace unmeasured values with estimates or synthetic-test results.

## Completed manual review and Colab handoff

The user completed all 72 review decisions: 18 litter, 30 clean and 24 skipped. The 48 included views contain 54 annotated litter regions from 11 panoramas and eight capture sequences. The agreed rule allows one tight box for touching tiny pieces that cannot be distinguished individually; distinguishable items receive separate boxes. Sixteen regions are under eight pixels along their smaller dimension at 640px detector input.

The usable views were exported to `data/pune-test-v1/` and reserved entirely for evaluation. `evaluation-lock.json` records image and label hashes, a fixed 0.35 confidence threshold, IoU 0.50, related capture sequences, exclusions and limitations. No Pune test photos enter the TACO training split. Most excluded views have the nonspecific note `NA`; the first score must disclose these exclusions and does not establish full-sphere or citywide performance.

A 4.79 GB Colab bundle and updated notebook are ready under `artifacts/colab/`. Archive CRC and file counts passed; labels and review image checksums were verified. Eight targeted review/data tests passed and all notebook code cells compiled. The pinned training package versions were available on the official Python package registry. No Colab GPU training or real model evaluation has run yet. See `docs/COLAB_RUN.md` for the handoff.

## Dataset record

Record the annotation source and hash, image licences, capture grouping method, number of images/groups per split, training settings, software versions, trained model hash and threshold chosen using validation data. Keep geographically or visually related frames together. Select the held-out Pune test set before evaluating and document its sampling method.

## Model results

Run `training/evaluate.py` and attach the emitted JSON. Include total labelled litter objects, true positives, false positives and false negatives, precision, recall, confidence threshold and IoU threshold. Include clean views, small distant rubbish, shadows, leaves, vehicles, occlusion and piles outside the one-class scope. Show example mistakes as well as successes.

Target roughly 50 held-out Pune views. A small test set is useful for a college prototype but does not establish citywide accuracy. An empty detection list means the model did not detect litter in the scanned view, not that the street is clean.

## 85% acceptance target

The user requires at least 85% measured litter-detection performance. For object detection, use **precision >= 0.85 and recall >= 0.85**, both on a separately reviewed Pune test set at box IoU >= 0.50. Precision is the share of proposed litter boxes that match real litter; recall is the share of labelled litter objects found. Report both values and the underlying TP, FP and FN counts; a model confidence score is not an accuracy result. Record mAP50 and mAP50-95 from training validation as supporting metrics, but do not substitute them for the two acceptance measures.

Lock the Pune test images and labels before tuning the detection threshold. Keep photographs from the same panorama, capture sequence or nearby repeated scene in one split. Include litter, verified clean views and difficult lookalikes from multiple streets and capture dates. The roughly 50-view target is an initial college-demo evaluation; add more independent views and report uncertainty when making broader claims. If either metric is undefined, the test set is inadequate and does not pass. Run `training/evaluate.py` with the deployed ONNX model and its fixed threshold, then inspect the complete six-view panorama output for duplicate boxes and alignment. The 85% claim remains **unverified** until real test data and trained weights meet these checks.

## Spatial and interface checks

Search for a place, check its blue pin and use **Open street view**. Verify that detection starts automatically and that tags remain attached to litter near panorama seams and overlapping view boundaries, after rotating/zooming, resizing and fullscreen. Inspect duplicate suppression on real objects crossing a view boundary. Selecting a result must turn the viewer toward the object and show boxes from only that result's evidence view. Change places/images during analysis: old-image results must not appear on the new image. Confirm source attribution, original capture dates and camera-position labels. Repeat at mobile width.

## Deployment measurements

Measure the first request after a fresh deployment, complete six-view inference on uncached panoramas, and cached reads separately. Targets are 30 seconds for first analysis and 10 seconds for repeat uncached analysis; these are goals, not measured performance. The entire response must complete within the configured 60-second hosting limit. The 45-second processing check is cooperative; a long individual download or inference can still exceed it. Record network/image-download time, function duration, peak memory, model size, six-preview response size and complete Python bundle size. A cached result is not evidence of faster model inference.

Attach a public deployment URL, date, browser versions and a short screen recording of a real scan. Until credentials and model artifacts are configured, describe the deployment as a setup preview.

## Baseline v1 result and v2 plan — 26 September 2026

The first Colab run (YOLO26n, 640px) scored **0 of 54** Pune regions at confidence 0.35 and IoU 0.50 (TP 0, FP 21, FN 54). It is **rejected**; the backend now refuses to serve its hash. Details and preserved files: `docs/BASELINE_V1.md`, `artifacts/runs/baseline-v1/`.

What the saved results already show: the model made only 21 predictions; 13 were in one panorama; only four views had both a false alarm and a miss, so box placement or cluster labelling can explain at most 4 matches. Letterboxing is an identity operation on the 640×640 test views, and the labels match the reviewer's boxes. The Pune per-image results have been inspected for diagnosis and are not used for tuning or selection.

Next steps, all model work in Colab: diagnosis notebook A (`docs/COLAB_RUN_V2.md`), manual TACO review (`docs/DATA_QUALITY.md`), then at most three experiments selected on a street-like TACO validation proxy, and one locked Pune evaluation. A 1024px copy of the locked Pune views (`data/pune-test-v1-r1024/`, labels unchanged, re-rendering verified byte-identical at 640px) supports the tiling experiment. Reaching 85% at 640px would require detecting at least 8 of the 16 regions under 8 pixels; that ceiling is why the higher-resolution option is included. The 85% target remains unmet and unverified.
