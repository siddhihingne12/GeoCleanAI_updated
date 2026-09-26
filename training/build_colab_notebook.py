"""Build the Colab notebook for the versioned local training bundle."""
import json
import textwrap
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    bundle = root / 'artifacts/colab'
    digest = (bundle / 'geocleanai-colab-data-v1.zip.sha256').read_text().strip()
    cells = []

    def add(kind, source):
        cell = {'cell_type': kind, 'metadata': {}, 'source': textwrap.dedent(source).strip().splitlines(keepends=True)}
        if kind == 'code':
            cell.update(execution_count=None, outputs=[])
        cells.append(cell)

    add('markdown', '''
        # GeoCleanAI — first Colab training run

        1. In Google Drive, create a folder named **GeoCleanAI** and upload `geocleanai-colab-data-v1.zip` into it.
        2. Open this notebook in Google Colab. Select **Runtime → Change runtime type → T4 GPU** (or another available GPU).
        3. Run the cells from top to bottom and allow Colab to connect to your Drive.

        If the dependency cell asks for a restart, choose **Runtime → Restart session**, then run the cells again from the top. This reloads upgraded libraries. Keep the same runtime and uploaded ZIP.

        Training uses the TACO split: **999 train / 324 validation / 177 test images**. The separate Pune test snapshot has **48 human-reviewed views: 18 litter, 30 clean, 54 litter regions**. It is reserved for evaluation and is never passed to training.

        This is a first baseline. Both Pune precision and recall must reach 85% at the fixed threshold to meet the numerical target. No score has been measured yet. The Pune sample is small and related views are correlated; 24 skipped views are excluded. Full-panorama alignment and timing still require separate validation. Free Colab GPU availability and runtime length vary.
    ''')
    add('code', '''
        from google.colab import drive
        drive.mount('/content/drive')
        from pathlib import Path
        DRIVE = Path('/content/drive/MyDrive/GeoCleanAI')
        ARCHIVE = DRIVE / 'geocleanai-colab-data-v1.zip'
        assert ARCHIVE.is_file(), 'Upload geocleanai-colab-data-v1.zip into My Drive/GeoCleanAI first.'
        ROOT = Path('/content/geocleanai-v1')
    ''')
    add('markdown', '## Check and unpack the data\nThe archive is several GB. This cell verifies the upload and unpacks it onto the Colab disk for training.')
    add('code', f'''
        import hashlib, zipfile
        EXPECTED_SHA256 = '{digest}'
        marker = ROOT / '.bundle-sha256'
        if not marker.is_file() or marker.read_text().strip() != EXPECTED_SHA256:
            with ARCHIVE.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            assert actual == EXPECTED_SHA256, 'The archive is incomplete or a different version. Finish the upload and retry.'
            ROOT.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(ARCHIVE) as bundle:
                for name in bundle.namelist():
                    assert (ROOT / name).resolve().is_relative_to(ROOT.resolve()), 'Unsafe archive path'
                bundle.extractall(ROOT)
            marker.write_text(EXPECTED_SHA256)
        print('Data ready:', ROOT)
    ''')
    add('code', '''
        import sys, subprocess
        from importlib.metadata import version, PackageNotFoundError
        package_roots = {'Pillow': 'PIL', 'numpy': 'numpy', 'torch': 'torch',
                         'torchvision': 'torchvision', 'pydantic': 'pydantic',
                         'pydantic_core': 'pydantic_core', 'ultralytics': 'ultralytics',
                         'onnxruntime': 'onnxruntime'}
        def installed_version(name):
            try:
                return version(name)
            except PackageNotFoundError:
                return None
        restart_message = ('Choose Runtime > Restart session, then run the notebook from the top. '
                           'Keep the same runtime and uploaded ZIP; do not delete the runtime.')
        if getattr(sys, '_geoclean_restart_required', False):
            raise RuntimeError(restart_message)
        before = {name: installed_version(name) for name in package_roots}
        loaded_before = set(sys.modules)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-r', str(ROOT / 'code/training/requirements.txt')], check=True)
        changed_loaded = [name for name, module in package_roots.items()
                          if before[name] != installed_version(name)
                          and any(key == module or key.startswith(module + '.') for key in loaded_before)]
        if changed_loaded:
            sys._geoclean_restart_required = True
            raise RuntimeError('Updated libraries were already loaded: ' + ', '.join(changed_loaded) + '. ' + restart_message)
        # Test the complete YOLO import before starting any training run.
        probe = subprocess.run([sys.executable, '-c',
                                'from PIL import Image, ImageDraw, ImageFont; from ultralytics import YOLO; print("Fresh imports OK")'],
                               capture_output=True, text=True)
        if probe.returncode:
            print(probe.stdout)
            print(probe.stderr)
            raise RuntimeError('Training imports fail even in a fresh process. Share the error above so the installation can be repaired.')
        try:
            from PIL import Image, ImageDraw, ImageFont
            from ultralytics import YOLO
        except (ImportError, AttributeError, ValueError) as error:
            sys._geoclean_restart_required = True
            raise RuntimeError('Fresh imports passed, but this session has stale library state. ' + restart_message) from error
        import torch
        assert torch.cuda.is_available(), 'Select Runtime > Change runtime type > GPU, then reconnect and rerun.'
        print('GPU:', torch.cuda.get_device_name(0))
    ''')
    add('code', '''
        import json
        from datetime import datetime, timezone
        DATA = ROOT / 'dataset/dataset.yaml'
        PUNE = ROOT / 'pune-test'
        summary = json.loads((ROOT / 'data-summary.json').read_text())
        lock = json.loads((PUNE / 'evaluation-lock.json').read_text())
        def file_hash(path):
            with path.open('rb') as stream:
                return hashlib.file_digest(stream, 'sha256').hexdigest()
        assert file_hash(ROOT / 'dataset/splits.json') == summary['training_split_sha256']
        assert file_hash(PUNE / 'evaluation-lock.json') == summary['test_lock_sha256']
        for row in lock['files']:
            assert file_hash(PUNE / 'images' / row['image']) == row['image_sha256']
            assert file_hash(PUNE / 'labels' / (Path(row['image']).stem + '.txt')) == row['label_sha256']
        OUTPUT = DRIVE / 'training-output' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        OUTPUT.mkdir(parents=True, exist_ok=True)
        print('TACO splits:', summary['training_split'])
        print('Reserved Pune test:', lock['test_images'], 'views;', lock['litter_regions'], 'litter regions')
        print('Checkpoints and results will be saved to:', OUTPUT)
    ''')
    add('markdown', '''
        ## Train and export
        This first run uses YOLO26n with 640px input for up to 50 epochs and early stopping. Checkpoints save to Drive. This follows the [Ultralytics YOLO26 training and export workflow](https://docs.ultralytics.com/models/yolo26/). A generic pretrained model becomes a litter detector only after this fine-tuning run.
    ''')
    add('code', '''
        sys.path.insert(0, str(ROOT / 'code'))
        from argparse import Namespace
        from training.train import train
        train(Namespace(data=DATA, output=OUTPUT, version='pune-litter-baseline-v1', epochs=50, resume=None))
    ''')
    add('markdown', '''
        ### Resume after a disconnect (only when needed)
        Reconnect a GPU, run the setup cells again, then set OUTPUT below to the previous run's Drive folder. Uncomment the two lines and run this cell instead of starting new training.
    ''')
    add('code', '''
        # OUTPUT = DRIVE / 'training-output' / 'REPLACE-WITH-PREVIOUS-RUN-FOLDER'
        # train(Namespace(data=DATA, output=OUTPUT, version='pune-litter-baseline-v1', epochs=50, resume=OUTPUT / 'runs/litter/weights/last.pt'))
    ''')
    add('markdown', '''
        ## Evaluate against your Pune labels
        Use the fixed 0.35 confidence threshold established before this run. Do not use these Pune test images to select training settings or tune the threshold. Future tuning needs separate validation data from other capture groups. The optional PyTorch comparison below checks that the ONNX export matches the trained model.
    ''')
    add('code', '''
        # Repair the evaluator shipped in the existing v1 data ZIP.
        # Safe to rerun; preserves the model, labels, and fixed threshold.
        import importlib
        evaluator_path = ROOT / 'code/training/evaluate.py'
        source = evaluator_path.read_text()
        old = 'return inter/union if union > 0 else 0'
        fixed = 'return float(inter / union) if union > 0 else 0.0'
        assert old in source or fixed in source, 'Unexpected evaluator version; check before patching.'
        if old in source:
            evaluator_path.write_text(source.replace(old, fixed))
        evaluate = importlib.reload(importlib.import_module('training.evaluate')).evaluate
        model_manifest = json.loads((OUTPUT / 'manifest.json').read_text())
        assert model_manifest['confidence_threshold'] == lock['confidence_threshold']
        assert file_hash(OUTPUT / 'litter.onnx') == model_manifest['sha256']
        evaluate(Namespace(model=OUTPUT / 'litter.onnx', dataset=PUNE,
                           output=OUTPUT / 'pune-evaluation.json', confidence=lock['confidence_threshold'],
                           pt=OUTPUT / 'best.pt'))
        result = json.loads((OUTPUT / 'pune-evaluation.json').read_text())
        result['evaluation_lock_sha256'] = summary['test_lock_sha256']
        result['skipped_views'] = len(lock['excluded'])
        result['limitations'] = lock['limitations'][:-1]
        result['numerical_target_met'] = all(result.get(k) is not None and result[k] >= .85 for k in ('precision', 'recall'))
        (OUTPUT / 'pune-evaluation.json').write_text(json.dumps(result, indent=2))
        print('Precision:', result['precision'], 'Recall:', result['recall'])
        print('85% numerical target met:', result['numerical_target_met'])
        print('ONNX/PyTorch agreement:', result['parity_passed'])
        print('Full panorama alignment and timing still need validation.')
    ''')
    add('markdown', '## Download your trained model and results\nThe zip also remains in your Google Drive run folder. Bring it back to the project so the model can be checked and installed.')
    add('code', '''
        import shutil
        shutil.copy2(PUNE / 'evaluation-lock.json', OUTPUT / 'evaluation-lock.json')
        shutil.copy2(ROOT / 'data-summary.json', OUTPUT / 'data-summary.json')
        result_zip = OUTPUT / 'geocleanai-model-and-results.zip'
        with zipfile.ZipFile(result_zip, 'w', zipfile.ZIP_DEFLATED) as bundle:
            for name in ['litter.onnx', 'manifest.json', 'best.pt', 'metrics.json',
                         'pune-evaluation.json', 'evaluation-lock.json', 'data-summary.json']:
                bundle.write(OUTPUT / name, name)
        print('Saved:', result_zip)
        from google.colab import files
        files.download(str(result_zip))
    ''')
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}, 'colab': {'name': 'GeoCleanAI_Training.ipynb'},
        'accelerator': 'GPU'}, 'cells': cells}
    for index, cell in enumerate(cells):
        cell['id'] = f'geoclean-{index}'
        if cell['cell_type'] == 'code':
            compile(''.join(cell['source']), f'cell-{index}', 'exec')
    for destination in [root / 'training/GeoCleanAI_Training.ipynb', bundle / 'GeoCleanAI_Training.ipynb']:
        destination.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Wrote notebook with {len(cells)} cells; all code cells compile.')


if __name__ == '__main__':
    main()
