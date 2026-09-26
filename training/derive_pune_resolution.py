"""Re-render the locked Pune test views at another resolution from the original panoramas.

Labels are normalized to the view, and the reviewer drew them on higher-resolution renders
of the same view geometry, so they are copied byte-for-byte. The source test set is never
modified. Before writing anything, every view is re-rendered at 640px and must reproduce
the locked JPEG byte-for-byte; otherwise the derived set would not be the same benchmark.
"""
import argparse
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.geometry import perspective
from backend.panorama import panorama_views


def sha256(path: Path) -> str:
    with path.open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def derive(source: Path, output: Path, longest_side: int, root: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output folder; derived test sets are never overwritten.')
    lock_path = source/'evaluation-lock.json'
    lock = json.loads(lock_path.read_text())
    views = {v['file_name']: v for v in json.loads((source/'manifest.json').read_text())['views']}
    geometry = dict(panorama_views())
    renders, checks = [], []
    panoramas = {}
    for row in lock['files']:
        name = row['image']
        if sha256(source/'images'/name) != row['image_sha256'] or sha256(source/'labels'/f'{Path(name).stem}.txt') != row['label_sha256']:
            raise ValueError(f'{name} does not match the evaluation lock.')
        view = views[name]
        original = root/Path(view['source_file'].replace('\\', '/'))
        if original not in panoramas:
            panoramas[original] = Image.open(original).convert('RGB')
        panorama = panoramas[original]
        if list(panorama.size) != view['panorama_size']:
            raise ValueError(f'{original} is not the panorama the test view was rendered from.')
        spec = geometry[view['view_id']]
        # Same renderer and encoder must reproduce the locked file byte-for-byte.
        buffer = io.BytesIO()
        perspective(panorama, spec, longest_side=640).save(buffer, format='JPEG', quality=92)
        checks.append(hashlib.sha256(buffer.getvalue()).hexdigest() == row['image_sha256'])
        renders.append((name, perspective(panorama, spec, longest_side=longest_side)))
    if not all(checks):
        raise ValueError(f'Re-rendering reproduced only {sum(checks)}/{len(checks)} locked views byte-for-byte.')
    (output/'images').mkdir(parents=True); (output/'labels').mkdir()
    files = []
    for (name, image), row in zip(renders, lock['files']):
        image.save(output/'images'/name, format='JPEG', quality=92)
        label = output/'labels'/f'{Path(name).stem}.txt'
        label.write_bytes((source/'labels'/label.name).read_bytes())
        files.append({**row, 'image_sha256': sha256(output/'images'/name), 'label_sha256': sha256(label)})
    version = lock.get('version', source.name)
    derived = {'version': f"{version}-r{longest_side}", 'role': lock['role'],
               'derived_from': version, 'parent_lock_sha256': sha256(lock_path),
               'longest_side': longest_side, 'labels': 'copied unchanged from the parent lock',
               # Test-only fields are carried over when present; train/validation split locks lack them.
               **{k: lock[k] for k in ('confidence_threshold', 'iou_threshold', 'annotation_rule', 'litter_regions', 'excluded', 'limitations', 'split_rule') if k in lock},
               'test_images': len(files),
               'determinism_check': {'rendered_at': 640, 'byte_identical_views': sum(checks), 'views': len(checks)},
               'created_at': datetime.now(timezone.utc).isoformat(), 'files': files}
    (output/'evaluation-lock.json').write_text(json.dumps(derived, indent=2))
    (output/'manifest.json').write_bytes((source/'manifest.json').read_bytes())
    return {'views': len(files), 'longest_side': longest_side, **derived['determinism_check']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('data/pune-test-v1'))
    parser.add_argument('--output', type=Path, default=Path('data/pune-test-v1-r1024'))
    parser.add_argument('--longest-side', type=int, default=1024)
    parser.add_argument('--root', type=Path, default=Path('.'), help='Folder that source_file paths are relative to')
    args = parser.parse_args()
    print(derive(args.source, args.output, args.longest_side, args.root))
