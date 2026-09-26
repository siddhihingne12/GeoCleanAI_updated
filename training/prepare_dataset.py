"""Convert reviewed COCO litter boxes to a reproducible, group-separated YOLO dataset.

Use TACO's reviewed annotations.json, not annotations_unofficial.json. Images must
already be downloaded, and all related captures must share a group in groups.json.
"""
import argparse
import csv
import hashlib
import json
import random
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image

def prepare(annotations: Path, images: Path, groups_path: Path, output: Path, seed: int = 42):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output directory to avoid mixing dataset versions.')
    coco = json.loads(annotations.read_text(encoding='utf-8'))
    groups = json.loads(groups_path.read_text(encoding='utf-8'))
    grouped = defaultdict(list)
    by_image = defaultdict(list)
    for ann in coco['annotations']:
        by_image[ann['image_id']].append(ann)
    # Merge any groups containing exact image duplicates before splitting.
    parent = {}
    def root(g):
        parent.setdefault(g, g)
        if parent[g] != g:
            parent[g] = root(parent[g])
        return parent[g]
    hashes = {}
    records = []
    image_root = images.resolve()
    for item in coco['images']:
        relative = item['file_name']
        source = (images / relative).resolve()
        if not source.is_relative_to(image_root) or not source.is_file():
            raise ValueError(f'Missing or unsafe image path: {relative}')
        group = groups.get(str(item['id']))
        if not isinstance(group, str) or not group:
            raise ValueError(f'Image {item["id"]} needs a capture/sequence group in groups.json.')
        with source.open('rb') as file:
            digest = hashlib.file_digest(file, 'sha256').hexdigest()
        if digest in hashes:
            parent[root(group)] = root(hashes[digest])
        hashes[digest] = group
        root(group)
        records.append((item, source, group, digest))
    for item, source, group, digest in records:
        grouped[root(group)].append((item, source, digest))
    keys = sorted(grouped)
    if len(keys) < 5:
        raise ValueError('At least five independent capture groups are required for a useful split.')
    random.Random(seed).shuffle(keys)
    validation_count = max(1, round(len(keys)*.15)); test_count = max(1, round(len(keys)*.15))
    splits = {g: ('val' if i < validation_count else 'test' if i < validation_count+test_count else 'train') for i, g in enumerate(keys)}
    output.mkdir(parents=True, exist_ok=True)
    split_records, credits = [], []
    license_lookup = {row['id']: row for row in coco.get('licenses', [])}
    for group, rows in grouped.items():
        split = splits[group]
        for item, source, digest in rows:
            with Image.open(source) as image:
                width, height = image.size
            if width != item['width'] or height != item['height']:
                raise ValueError(f'Image dimensions differ from annotations: {source.name}. Use original images.')
            image_dir, label_dir = output/'images'/split, output/'labels'/split
            image_dir.mkdir(parents=True, exist_ok=True); label_dir.mkdir(parents=True, exist_ok=True)
            name = f'{item["id"]}{source.suffix.lower()}'
            shutil.copy2(source, image_dir/name)
            labels = []
            for ann in by_image[item['id']]:
                x, y, w, h = ann['bbox']
                x1, y1 = max(0,x), max(0,y); x2, y2 = min(width,x+w), min(height,y+h)
                if x2 > x1 and y2 > y1:
                    labels.append(f'0 {(x1+x2)/(2*width):.8f} {(y1+y2)/(2*height):.8f} {(x2-x1)/width:.8f} {(y2-y1)/height:.8f}')
            (label_dir/f'{item["id"]}.txt').write_text('\n'.join(labels), encoding='utf-8')
            split_records.append({'id': item['id'], 'group': group, 'split': split, 'sha256': digest, 'source': item['file_name'], 'objects': len(labels)})
            license_info = license_lookup.get(item.get('license'), {})
            credits.append({'image_id': item['id'], 'source_url': item.get('flickr_url') or item.get('coco_url') or '', 'license': license_info.get('name') or item.get('license') or 'Check original image source', 'license_url': license_info.get('url', '')})
    # Relative path makes the prepared folder portable between Colab and local runs.
    (output/'dataset.yaml').write_text('path: .\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: litter\n', encoding='utf-8')
    (output/'splits.json').write_text(json.dumps({'seed': seed, 'annotation_sha256': hashlib.sha256(annotations.read_bytes()).hexdigest(), 'images': split_records}, indent=2), encoding='utf-8')
    with (output/'credits.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['image_id','source_url','license','license_url']); writer.writeheader(); writer.writerows(credits)
    return {split: sum(r['split'] == split for r in split_records) for split in ('train','val','test')}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, required=True)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--groups', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()
    print(prepare(args.annotations, args.images, args.groups, args.output, args.seed))
