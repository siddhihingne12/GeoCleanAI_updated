"""Package the prepared TACO split and a separate, locked Pune test snapshot."""
import hashlib
import json
import math
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_labels(path):
    count = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        values = list(map(float, line.split()))
        if len(values) != 5 or not all(math.isfinite(v) for v in values):
            raise ValueError(f'Invalid label: {path}')
        cls, x, y, width, height = values
        if cls != 0 or not (0 < width <= 1 and 0 < height <= 1):
            raise ValueError(f'Invalid litter box: {path}')
        if min(x-width/2, y-height/2) < -1e-7 or max(x+width/2, y+height/2) > 1+1e-7:
            raise ValueError(f'Box outside image: {path}')
        count += 1
    return count


def main():
    root = Path(__file__).resolve().parents[1]
    dataset = root / 'data/litter'
    test = root / 'data/pune-test-v1'
    output = root / 'artifacts/colab'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / 'geocleanai-colab-data-v1.zip'
    if archive.exists():
        raise ValueError('The Colab archive already exists; keep this version unchanged.')

    splits = json.loads((dataset / 'splits.json').read_text())['images']
    group_splits = {}
    for row in splits:
        previous = group_splits.setdefault(row['group'], row['split'])
        if previous != row['split']:
            raise ValueError('A TACO capture group crosses splits')
    training_counts = Counter(row['split'] for row in splits)
    training_boxes = sum(validate_labels(path) for path in (dataset / 'labels').rglob('*.txt'))
    for row in splits:
        image = dataset / 'images' / row['split'] / f"{row['id']}{Path(row['source']).suffix.lower()}"
        label = dataset / 'labels' / row['split'] / f"{row['id']}.txt"
        if not image.is_file() or not label.is_file():
            raise ValueError('The TACO split has missing files')

    manifest = json.loads((test / 'manifest.json').read_text())
    entries = []
    test_boxes = 0
    for row in manifest['views']:
        name = row['file_name']
        image = test / 'images' / name
        label = test / 'labels' / f'{Path(name).stem}.txt'
        boxes = validate_labels(label)
        if sha(image) != row['review']['sha256']:
            raise ValueError(f'Reviewed image changed: {name}')
        if (row['review']['status'] == 'litter') != bool(boxes):
            raise ValueError(f'Review and label disagree: {name}')
        test_boxes += boxes
        entries.append({'image': name, 'sequence': row['sequence'],
                        'image_sha256': sha(image), 'label_sha256': sha(label), 'boxes': boxes})
    all_reviews = []
    for path in sorted((root / 'data/pune-review/reviews').glob('*.json')):
        review = json.loads(path.read_text())
        all_reviews.append({'file_name': path.name.removesuffix('.json'), **review})
    statuses = Counter(row['status'] for row in all_reviews)
    snapshot = {
        'version': 'pune-test-v1', 'role': 'held_out_evaluation_only',
        'locked_at': datetime.now(timezone.utc).isoformat(),
        'confidence_threshold': .35, 'iou_threshold': .5,
        'annotation_rule': 'One box per distinguishable item; one tight box for a touching tiny cluster whose pieces cannot be separated.',
        'review_counts': dict(statuses), 'test_images': len(entries), 'litter_regions': test_boxes,
        'panoramas': len({row['image_id'] for row in manifest['views']}),
        'capture_sequences': len({row['sequence'] for row in entries}),
        'excluded': [{'image': row['file_name'], 'reason': row.get('notes', '')}
                     for row in all_reviews if row['status'] not in {'litter', 'clean'}],
        'limitations': ['Views within a panorama or sequence are correlated.',
                       'Skipped views are excluded, so this does not measure all six directions.',
                       'Most skip notes say NA and do not identify the exclusion reason.',
                       'Compact clusters count as regions rather than individual litter pieces.',
                       'No model has been evaluated yet.'],
        'files': entries,
    }
    lock = test / 'evaluation-lock.json'
    if lock.exists():
        old = json.loads(lock.read_text())
        if old['files'] != entries:
            raise ValueError('Locked Pune images or labels changed')
        snapshot = old
    else:
        lock.write_text(json.dumps(snapshot, indent=2), encoding='utf-8')

    summary = {'training_source': 'TACO reviewed annotations', 'training_split': dict(training_counts),
               'taco_boxes': training_boxes, 'taco_capture_groups': len(group_splits),
               'pune_test': {k: v for k, v in snapshot.items() if k != 'files'},
               'test_lock_sha256': sha(lock), 'training_split_sha256': sha(dataset / 'splits.json')}
    (output / 'data-summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    files = []
    for directory, prefix in [(dataset, 'dataset'), (test, 'pune-test')]:
        files.extend((p, f'{prefix}/{p.relative_to(directory).as_posix()}')
                     for p in sorted(directory.rglob('*')) if p.is_file())
    for relative in ['training/train.py', 'training/evaluate.py', 'training/requirements.txt',
                     'backend/geometry.py', 'backend/schemas.py']:
        files.append((root / relative, f'code/{relative}'))
    files.append((output / 'data-summary.json', 'data-summary.json'))
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as bundle:
        for index, (source, target) in enumerate(files, 1):
            bundle.write(source, target)
            if index % 500 == 0:
                print(f'Packed {index}/{len(files)} files', flush=True)
        bundle.writestr('code/training/__init__.py', '')
        bundle.writestr('code/backend/__init__.py', '')
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.namelist()) != len(files) + 2:
            raise ValueError('Archive file count differs')
        if bundle.testzip() is not None:
            raise ValueError('Archive checksum validation failed')
    digest = sha(archive)
    archive.with_suffix('.zip.sha256').write_text(digest, encoding='ascii')
    print(json.dumps({'archive': str(archive), 'bytes': archive.stat().st_size,
                      'sha256': digest, 'training_split': dict(training_counts),
                      'pune_test_images': len(entries), 'pune_litter_regions': test_boxes}, indent=2))


if __name__ == '__main__':
    main()
