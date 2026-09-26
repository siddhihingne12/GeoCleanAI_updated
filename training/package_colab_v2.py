"""Package code, the preserved baseline and derived data for the v2 Colab notebooks.

The 4.79 GB v1 data zip already on Drive holds the TACO originals and the locked Pune test.
This archive adds only what is new. For derived datasets, original TACO photos are not
repeated: the notebook copies them from the unpacked v1 dataset and checks every hash
recorded here, so the Colab copy is byte-identical to the local one.
"""
import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ['training/*.py', 'training/experiments/*.json', 'training/requirements.txt', 'backend/*.py',
        'tests/python/conftest.py', 'tests/python/test_evaluate.py', 'tests/python/test_diagnose.py',
        'tests/python/test_derivatives.py', 'tests/python/test_geometry.py', 'tests/python/test_panorama.py', 'pyproject.toml']


def sha256(path: Path) -> str:
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def package(output: Path, datasets: list[str]):
    if output.exists():
        raise ValueError(f'{output.name} already exists; package a new version instead of replacing it.')
    entries, originals = {}, {}
    for pattern in CODE:
        for path in sorted(ROOT.glob(pattern)):
            entries[f'code/{path.relative_to(ROOT).as_posix()}'] = path
    for path in sorted((ROOT/'artifacts/runs/baseline-v1').rglob('*')):
        if path.is_file() and path.suffix != '.zip':
            entries[f'baseline-v1/{path.relative_to(ROOT/"artifacts/runs/baseline-v1").as_posix()}'] = path
    for path in sorted((ROOT/'data/pune-test-v1-r1024').rglob('*')):
        if path.is_file():
            entries[f'pune-test-v1-r1024/{path.relative_to(ROOT/"data/pune-test-v1-r1024").as_posix()}'] = path
    for name in datasets:
        folder = ROOT/'data'/name
        records = json.loads((folder/'splits.json').read_text())['images'] if (folder/'splits.json').is_file() else []
        # Derived files are named <id>_<profile>_<k>; originals keep the bare <id> stem.
        original_stems = {(r['split'], Path(r['name']).stem) for r in records if r['kind'] == 'original'}
        originals[name] = []
        for path in sorted(folder.rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(folder)
            parts = relative.parts
            if len(parts) == 3 and parts[0] in ('images', 'labels') and (parts[1], path.stem) in original_stems:
                originals[name].append({'path': relative.as_posix(), 'sha256': sha256(path)})
                continue
            entries[f'datasets/{name}/{relative.as_posix()}'] = path
    manifest = {'version': output.stem, 'created_at': datetime.now(timezone.utc).isoformat(),
                'requires': 'geocleanai-colab-data-v1.zip unpacked (TACO originals and locked Pune test)',
                'files': {name: sha256(path) for name, path in entries.items()},
                'originals_from_v1': originals}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, path in entries.items():
            archive.write(path, name)
        archive.writestr('bundle-manifest.json', json.dumps(manifest, indent=2))
    digest = sha256(output)
    output.with_name(output.name + '.sha256').write_text(digest + '\n')
    return {'archive': str(output), 'files': len(entries), 'originals_restored_in_colab': {k: len(v) for k, v in originals.items()},
            'megabytes': round(output.stat().st_size / 1e6, 1), 'sha256': digest}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/colab/geocleanai-colab-v2.zip')
    parser.add_argument('--datasets', nargs='*', default=[], help='Derived dataset folders under data/, e.g. litter-v2')
    args = parser.parse_args()
    print(json.dumps(package(args.output, args.datasets), indent=2))
