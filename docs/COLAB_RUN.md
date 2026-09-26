# First Colab training run

Your manual review is complete: 72 decisions, with 18 litter views, 30 clean views and 24 skipped views. The 48 usable views contain 54 marked litter regions and are reserved as `data/pune-test-v1/`. They cover 11 panoramas and eight capture sequences. No Pune test view is included in the training dataset.

## Files ready on this computer

Open `C:\Users\VINEET\Documents\GeoCleanAI\artifacts\colab`.

- `geocleanai-colab-data-v1.zip` — 4.79 GB, containing the TACO dataset, separate Pune test snapshot, training/evaluation code and source credits.
- `GeoCleanAI_Training.ipynb` — notebook for this exact bundle.
- `data-summary.json` — counts, exclusions and evaluation limitations.
- `geocleanai-colab-data-v1.zip.sha256` — checksum used by the notebook to detect an incomplete upload.

## Run on Google Colab

1. In Google Drive, create a folder named **GeoCleanAI** under **My Drive**.
2. Upload **geocleanai-colab-data-v1.zip** into that folder. Wait for the upload to finish.
3. Open [Google Colab](https://colab.research.google.com/). Choose **File → Upload notebook** and select **GeoCleanAI_Training.ipynb** from the local folder above.
4. Choose **Runtime → Change runtime type → T4 GPU**, or another available GPU.
5. Run the notebook cells in order. Allow Colab to connect to Drive when prompted.

If setup upgrades a library that Colab already loaded, the updated notebook stops and asks for **Runtime → Restart session**. Restart the session, then run the cells from the top. Keep the same VM and uploaded ZIP. This avoids mixing older in-memory Pillow/NumPy components with newly installed files. The notebook also tests the complete YOLO import in a fresh Python process before training.

For an existing notebook showing `cannot import name '_Ink' from 'PIL._typing'`, first restart the session and rerun from the top. Remove any proposed `Pillow==9.5.0` downgrade: the user's Colab is Python 3.13, which that Pillow release does not support. If the downgrade was already installed, reinstall the project's `Pillow==12.3.0`, restart the session, then rerun. The Ultralytics settings-file creation message is normal and unrelated to this import failure.

The notebook verifies the archive, copies data onto the Colab disk, installs the pinned training packages and starts a first YOLO26n training run for up to 50 epochs with early stopping. It follows the [official Ultralytics workflow](https://docs.ultralytics.com/models/yolo26/). Checkpoints and final files are saved under `My Drive/GeoCleanAI/training-output/<run-date>/`. GPU availability and runtime limits depend on Colab; no training run has been executed yet.

After training it exports ONNX, checks predictions against the PyTorch model and measures precision and recall on the reserved Pune test set using the fixed 0.35 confidence threshold. It produces **geocleanai-model-and-results.zip** containing `litter.onnx`, `manifest.json`, `best.pt`, model metrics, Pune results and the data records. The notebook includes a resume example for interrupted runs.

## Recover from `float32 is not JSON serializable` during evaluation

This error occurs while saving the ONNX/PyTorch comparison results. The box-overlap calculation returned a NumPy scalar. Training and export do not need to be repeated. The updated notebook repairs the evaluator included in the existing v1 ZIP before running evaluation.

For an already open Colab notebook, run this new cell immediately before the failed evaluation cell:

```python
from pathlib import Path
import importlib

path = Path('/content/geocleanai-v1/code/training/evaluate.py')
source = path.read_text()
old = 'return inter/union if union > 0 else 0'
fixed = 'return float(inter / union) if union > 0 else 0.0'
assert old in source or fixed in source, 'Unexpected evaluator version; share the current code.'
if old in source:
    path.write_text(source.replace(old, fixed))
evaluate = importlib.reload(importlib.import_module('training.evaluate')).evaluate
print('Evaluator repaired. Rerun the evaluation cell.')
```

Then rerun only the failed evaluation cell and, once it succeeds, the download cell. Keep the current session and `OUTPUT` folder: do not restart or Run all for this repair. No dataset reupload or dependency reinstall is needed. A custom JSON encoder would have to be passed to the `json.dumps` call inside `evaluate.py`; defining one elsewhere alone would not fix it.

## How to use the results

The target is **precision >= 85% and recall >= 85%** at IoU 0.50. The first run may fall short; its measured mistakes will guide further work. Preserve this Pune test set and collect separate Pune training and validation groups before tuning the model. Do not move these test photos into training or choose a threshold using their results.

The 24 skipped views remain excluded, with their original notes preserved. Most notes say `NA`; their precise reasons are unresolved. This first score covers the 48 labeled views, not the entire six-view pipeline or the whole city. Tiny touching clusters may use one box under the agreed rule, so counts describe litter regions rather than individual pieces. Sixteen of the 54 marked regions have a minimum side below eight pixels at the detector's 640px input; small-object misses are a concrete risk to measure.

The archive passed file-count and CRC checks. All 48 image checksums match the reviewed images, labels have valid coordinates, capture groups do not cross TACO splits, and notebook code cells compile. Actual GPU training, model performance, complete panorama alignment and hosting latency remain to be measured.
