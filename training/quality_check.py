"""Automated TACO quality checks and a manual review queue (Phase 2). No model involved.

Writes to an empty folder:
  quality-review.json  automated flags for every image, plus the rules used
  review-queue.csv     flagged images + a seeded stratified sample, for a human to fill in
  queue/<id>.jpg       each queued image with its boxes drawn, at most 1280px

Manual columns in review-queue.csv:
  status               usable | difficult | unusable   (only 'unusable' leaves training)
  annotation_complete  yes | no  (only 'yes' images may supply clean negative crops)
  tags                 any of: small clutter shadows leaves road_markings low_light glare occluded cluster
  notes                free text; required when status is 'unusable'
"""
import argparse
import csv
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from training.audit_taco_groups import dhash
from training.diagnose import laplacian_variance

RULES = {
    'litter': 'Discarded man-made waste: packaging, bottles, cans, bags, cups, paper, cigarette butts, wrappers, fragments.',
    'cluster': 'Touching pieces that cannot be told apart get one tight box; distinguishable pieces get separate boxes.',
    'confusers': 'Not litter: leaves, stones, soil clods, shadows, road markings, drain covers, bins, vehicle parts, signage, construction material, animal waste.',
    'unusable': 'Wrong or misaligned labels, corrupt image, or not a litter scene. Difficult-but-valid images (small, occluded, cluttered, shadowed, blurred) stay.',
    'clean': 'Never treat unlabelled, skipped or ambiguous images as clean. Negative crops only from images reviewed as annotation_complete=yes.',
}
TAGS = ('small', 'clutter', 'shadows', 'leaves', 'road_markings', 'low_light', 'glare', 'occluded', 'cluster')
QUEUE_FIELDS = ['image_id', 'file_name', 'split', 'group', 'reasons', 'status', 'annotation_complete', 'tags', 'notes']


def box_iou(a, b):
    ax1, ay1, aw, ah = a; bx1, by1, bw, bh = b
    inter = max(0, min(ax1+aw, bx1+bw)-max(ax1, bx1)) * max(0, min(ay1+ah, by1+bh)-max(ay1, by1))
    union = aw*ah + bw*bh - inter
    return inter/union if union > 0 else 0.0


def check_image(item: dict, annotations: list[dict], images: Path) -> dict:
    flags, path = [], images/item['file_name']
    try:
        with Image.open(path) as image:
            image.load()
            size, mode, orientation = image.size, image.mode, image.getexif().get(274, 1)
            scale = 1024 / max(image.size)
            gray = np.asarray(image.convert('L').resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.BILINEAR))
    except OSError as error:
        return {'flags': [f'unreadable: {error}'], 'sharpness': None, 'box_sharpness': []}
    if list(size) != [item['width'], item['height']]:
        flags.append('size differs from annotation')
    if orientation != 1:
        flags.append(f'EXIF orientation {orientation}')
    if mode != 'RGB':
        flags.append(f'mode {mode}')
    box_sharpness = []
    boxes = [a['bbox'] for a in annotations]
    for index, (x, y, w, h) in enumerate(boxes):
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x+w > size[0]+.5 or y+h > size[1]+.5:
            flags.append(f'box {index} outside image or empty')
        # Under 2 source pixels cannot hold a recognisable object at any scale.
        if min(w, h) < 2:
            flags.append(f'box {index} under 2px')
        x1, y1 = int(x*scale), int(y*scale)
        box_sharpness.append(laplacian_variance(gray[y1:int(np.ceil((y+h)*scale)), x1:int(np.ceil((x+w)*scale))]))
    for i in range(len(boxes)):
        for j in range(i+1, len(boxes)):
            if box_iou(boxes[i], boxes[j]) > .9:
                flags.append(f'boxes {i} and {j} near-duplicate')
    if not boxes:
        flags.append('no boxes (not verified clean)')
    return {'flags': flags, 'sharpness': laplacian_variance(gray), 'box_sharpness': box_sharpness}


def cross_split_pairs(rows: list[dict], maximum_distance: int) -> list[dict]:
    """Near-duplicate candidates whose images sit in different splits (possible leakage)."""
    pairs = []
    for i, left in enumerate(rows):
        for right in rows[i+1:]:
            if left['split'] == right['split']:
                continue
            distance = (left['hash'] ^ right['hash']).bit_count()
            if distance <= maximum_distance:
                pairs.append({'left': left['id'], 'right': right['id'], 'splits': [left['split'], right['split']], 'distance': distance})
    return sorted(pairs, key=lambda p: p['distance'])


def stratified_sample(records: list[dict], size: int, seed: int, exclude: set) -> list[int]:
    """Seeded sample across split x median box size so every stratum gets reviewed."""
    strata = defaultdict(list)
    for record in records:
        if record['id'] in exclude:
            continue
        sides = record['box_short_side_px_at_640']
        median = float(np.median(sides)) if sides else 0
        strata[(record['split'], '<16' if median < 16 else '16-32' if median < 32 else '>=32')].append(record['id'])
    rng, total = random.Random(seed), sum(len(v) for v in strata.values())
    chosen = []
    for key in sorted(strata):
        ids = sorted(strata[key])
        rng.shuffle(ids)
        chosen += ids[:max(1, round(size * len(ids) / total))]
    return sorted(chosen)


def draw_queue_image(path: Path, annotations: list[dict], output: Path):
    with Image.open(path) as image:
        scale = min(1, 1280 / max(image.size))
        image = image.convert('RGB').resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(image)
    for index, annotation in enumerate(annotations):
        x, y, w, h = (v*scale for v in annotation['bbox'])
        draw.rectangle([x, y, x+w, y+h], outline=(255, 0, 255), width=2)
        draw.text((x, max(0, y-11)), str(index), fill=(255, 0, 255))
    image.save(output, quality=88)


def run(annotations: Path, images: Path, splits: Path, credits: Path, output: Path, sample: int, seed: int, maximum_distance: int):
    if output.exists() and any(output.iterdir()):
        raise ValueError('Choose an empty output folder; earlier reviews are never overwritten.')
    coco = json.loads(annotations.read_text(encoding='utf-8'))
    split_rows = {r['id']: r for r in json.loads(splits.read_text())['images']}
    licences = {int(r['image_id']): r for r in csv.DictReader(credits.open(encoding='utf-8'))}
    by_image = defaultdict(list)
    for annotation in coco['annotations']:
        by_image[annotation['image_id']].append(annotation)
    records = []
    for item in coco['images']:
        checked = check_image(item, by_image[item['id']], images)
        scale = 640 / max(item['width'], item['height'])
        licence = licences.get(item['id'], {})
        if not licence.get('source_url'):
            checked['flags'].append('missing source URL')
        records.append({'id': item['id'], 'file_name': item['file_name'], 'split': split_rows[item['id']]['split'],
                        'group': split_rows[item['id']]['group'], 'boxes': len(by_image[item['id']]),
                        'box_short_side_px_at_640': [round(min(a['bbox'][2], a['bbox'][3])*scale, 1) for a in by_image[item['id']]],
                        'licence_resolved': bool(licence.get('license')) and licence.get('license') != 'Check original image source',
                        'hash': dhash(images/item['file_name']), **checked})
    sharp = np.array([r['sharpness'] for r in records if r['sharpness'] is not None])
    blur_floor = float(np.percentile(sharp, 5))
    for record in records:
        # Review aid only: blur is difficulty, not a reason to drop.
        if record['sharpness'] is not None and record['sharpness'] < blur_floor:
            record['flags'].append('whole-image sharpness in lowest 5% (review; blur alone is not unusable)')
    pairs = cross_split_pairs(records, maximum_distance)
    for pair in pairs:
        for side in ('left', 'right'):
            next(r for r in records if r['id'] == pair[side])['flags'].append(f"possible related image across splits: {pair['left']}/{pair['right']} (distance {pair['distance']})")
    flagged = {r['id'] for r in records if any(not f.startswith('no boxes') for f in r['flags'])}
    queue_ids = sorted(flagged | set(stratified_sample(records, sample, seed, flagged)))
    output.mkdir(parents=True, exist_ok=True)
    (output/'queue').mkdir()
    lookup = {r['id']: r for r in records}
    with (output/'review-queue.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=QUEUE_FIELDS); writer.writeheader()
        for image_id in queue_ids:
            record = lookup[image_id]
            writer.writerow({'image_id': image_id, 'file_name': record['file_name'], 'split': record['split'], 'group': record['group'],
                             'reasons': '; '.join(record['flags']) or 'stratified sample', 'status': '', 'annotation_complete': '', 'tags': '', 'notes': ''})
            draw_queue_image(images/record['file_name'], by_image[image_id], output/'queue'/f'{image_id}.jpg')
    for record in records:
        del record['hash']
    summary = {'images': len(records), 'flagged': len(flagged), 'queued': len(queue_ids), 'sample_seed': seed,
               'cross_split_candidates': len(pairs), 'hash_maximum_distance': maximum_distance,
               'licence_unresolved': sum(not r['licence_resolved'] for r in records),
               'flag_counts': dict(Counter(f.split(':')[0].split(' (')[0] for r in records for f in r['flags']).most_common()),
               'blur_review_floor': blur_floor}
    (output/'quality-review.json').write_text(json.dumps({'rules': RULES, 'tags': TAGS, 'summary': summary,
                                                          'cross_split_pairs': pairs, 'images': records}, indent=2), encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--annotations', type=Path, default=Path('data/TACO/annotations.json'))
    parser.add_argument('--images', type=Path, default=Path('data/TACO'))
    parser.add_argument('--splits', type=Path, default=Path('data/litter/splits.json'))
    parser.add_argument('--credits', type=Path, default=Path('data/litter/credits.csv'))
    parser.add_argument('--output', type=Path, default=Path('data/litter-review'))
    parser.add_argument('--sample', type=int, default=150)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--maximum-distance', type=int, default=24, help='Looser than the first 12-bit audit')
    args = parser.parse_args()
    print(json.dumps(run(args.annotations, args.images, args.splits, args.credits, args.output, args.sample, args.seed, args.maximum_distance), indent=2))
