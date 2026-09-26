"""Generate the portable Colab notebook from versioned project scripts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cells = []
def markdown(text):
    cells.append({'cell_type':'markdown','metadata':{},'source':text.splitlines(keepends=True)})
def code(text):
    cells.append({'cell_type':'code','execution_count':None,'metadata':{},'outputs':[],'source':text.splitlines(keepends=True)})

markdown('# GeoCleanAI — Train your litter detector\n\nUse a Colab GPU runtime. This notebook fine-tunes YOLO26n and exports a model for the website. It does not contain pretrained litter weights or claimed evaluation results.\n\nBefore running: upload your prepared dataset folder (dataset.yaml, splits.json, images/, labels/) to Google Drive. Prepare it with training/prepare_dataset.py using reviewed TACO annotations and capture groups. Keep a separate, labelled Pune evaluation set. Cite TACO and preserve each image’s licence.')
code('%pip install -q ultralytics==8.4.155 onnx==1.23.0 onnxruntime==1.30.0 PyYAML==6.0.3 Pillow==12.3.0 numpy==2.5.3')
code('from google.colab import drive\ndrive.mount("/content/drive")\nfrom pathlib import Path\nimport torch\nprint("GPU available:", torch.cuda.is_available())\nassert torch.cuda.is_available(), "Select Runtime > Change runtime type > GPU, then reconnect. Free GPU availability varies."')
code('DATA = Path("/content/drive/MyDrive/GeoCleanAI/dataset/dataset.yaml")\nOUTPUT = Path("/content/drive/MyDrive/GeoCleanAI/training-output")\nassert DATA.exists(), "Place your prepared dataset on Drive and update DATA."')
markdown('## Fine-tune and export\n\nCheckpoints are written to Drive. Keep the notebook open during training. The run uses 50 epochs with early stopping. If Colab disconnects, use the resume cell below.')
code((ROOT/'training/train.py').read_text().split("if __name__ == '__main__':")[0]+'\nfrom argparse import Namespace\ntrain(Namespace(data=DATA, output=OUTPUT, version="pune-litter-v1", epochs=50, resume=None))\n')
markdown('## Resume an interrupted run (optional)\n\nRun this cell only after an interrupted training run. Update the path to the most recent last.pt.')
code('# train(Namespace(data=DATA, output=OUTPUT, version="pune-litter-v1", epochs=50, resume=OUTPUT/"runs/litter/weights/last.pt"))')
markdown('## Download the artifacts\n\nPlace litter.onnx and manifest.json in the project’s models/ folder. Keep best.pt, metrics.json and the split manifest for your report. Run training/evaluate.py locally or in Colab on held-out Pune images; include --pt for ONNX parity. Do not describe TACO test scores as Pune accuracy.')
code('import shutil\nfrom google.colab import files\nshutil.make_archive("/content/geocleanai-model", "zip", OUTPUT)\nfiles.download("/content/geocleanai-model.zip")')
notebook = {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python'},'colab':{'name':'GeoCleanAI_Training.ipynb'}},'nbformat':4,'nbformat_minor':5}
(ROOT/'training/GeoCleanAI_Training.ipynb').write_text(json.dumps(notebook,indent=2),encoding='utf-8')
print('Created training/GeoCleanAI_Training.ipynb')
