"""Find likely cross-batch near duplicates before splitting TACO photos.

This is a review aid. A perceptual hash match is not proof of the same capture;
visually inspect the reported pairs before finalizing groups.json.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def dhash(path: Path) -> int:
    with Image.open(path) as image:
        pixels = np.asarray(image.convert('L').resize((17, 16), Image.Resampling.BILINEAR))
    bits = (pixels[:, 1:] > pixels[:, :-1]).ravel()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def audit(annotations: Path, images: Path, output: Path, maximum_distance: int) -> dict:
    coco = json.loads(annotations.read_text(encoding='utf-8'))
    rows = []
    for item in coco['images']:
        path = images / item['file_name']
        if not path.is_file():
            raise FileNotFoundError(path)
        rows.append({'id': item['id'], 'file_name': item['file_name'],
                     'batch': item['file_name'].split('/')[0], 'hash': dhash(path)})
    pairs = []
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if left['batch'] == right['batch']:
                continue
            distance = (left['hash'] ^ right['hash']).bit_count()
            if distance <= maximum_distance:
                pairs.append({'left': left['file_name'], 'right': right['file_name'],
                              'distance': distance})
    report = {'images': len(rows), 'hash_bits': 256, 'maximum_distance': maximum_distance,
              'cross_batch_candidates': sorted(pairs, key=lambda pair: pair['distance']),
              'note': 'Review each pair visually. Distant views of one scene may not match.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return {'images': len(rows), 'candidate_pairs': len(pairs), 'report': str(output)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, default=Path('data/TACO/annotations.json'))
    parser.add_argument('--images', type=Path, default=Path('data/TACO'))
    parser.add_argument('--output', type=Path, default=Path('data/TACO/group-audit.json'))
    parser.add_argument('--maximum-distance', type=int, default=12)
    args = parser.parse_args()
    if not 0 <= args.maximum_distance <= 256:
        parser.error('--maximum-distance must be from 0 to 256')
    print(audit(args.annotations, args.images, args.output, args.maximum_distance))
