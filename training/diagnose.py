"""Diagnosis helpers for a trained model. Run in Colab; nothing here trains or tunes.

Inputs are evaluation JSON files written by training/evaluate.py. Pune test results are
inspected here for diagnosis only: nothing computed here may choose a threshold, a
model or which examples to keep.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from training.evaluate import iou, short_side_px, size_bucket

IMAGE_SUFFIXES = ('.jpg', '.jpeg', '.png')


def sha256(path: Path) -> str:
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


# --- 1. Integrity -------------------------------------------------------------------

def checkpoint_metadata(pt_path: Path) -> dict:
    """What the checkpoint itself records (Ultralytics strips some fields from best.pt)."""
    import torch
    ckpt = torch.load(str(pt_path), map_location='cpu', weights_only=False)
    model = ckpt.get('model') or ckpt.get('ema')
    return {'sha256': sha256(pt_path), 'ultralytics_version': ckpt.get('version'), 'date': ckpt.get('date'),
            'epoch': ckpt.get('epoch'), 'best_fitness': ckpt.get('best_fitness'),
            'names': getattr(model, 'names', None), 'train_args': ckpt.get('train_args'),
            'train_metrics': ckpt.get('train_metrics'), 'train_results': ckpt.get('train_results')}


def pairing_report(dataset: Path, splits=('train', 'val', 'test')) -> dict:
    """Every image has exactly one label file and vice versa; labels are valid class-0 YOLO boxes."""
    report = {}
    for split in splits:
        images = {p.stem for p in (dataset/'images'/split).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES}
        labels = {p.stem for p in (dataset/'labels'/split).glob('*.txt')}
        invalid = []
        for stem in sorted(labels):
            for number, line in enumerate((dataset/'labels'/split/f'{stem}.txt').read_text().splitlines(), 1):
                if not line.strip():
                    continue
                values = line.split()
                if len(values) != 5:
                    invalid.append(f'{stem}:{number}')
                    continue
                cls, x, y, w, h = map(float, values)
                # Small tolerance for 8-decimal rounding at image edges.
                inside = -1e-6 <= x-w/2 and x+w/2 <= 1+1e-6 and -1e-6 <= y-h/2 and y+h/2 <= 1+1e-6
                if cls != 0 or w <= 0 or h <= 0 or not inside:
                    invalid.append(f'{stem}:{number}')
        report[split] = {'images': len(images), 'labels': len(labels), 'images_without_label': sorted(images-labels)[:20],
                         'labels_without_image': sorted(labels-images)[:20], 'invalid_label_lines': invalid[:20],
                         'invalid_count': len(invalid)}
    return report


# --- 2. Training curves -------------------------------------------------------------

def read_results(source) -> dict[str, list[float]]:
    """results.csv path, or the train_results dict stored in a checkpoint."""
    if isinstance(source, dict):
        return {k.strip(): [float(v) for v in values] for k, values in source.items()}
    with Path(source).open() as file:
        rows = list(csv.DictReader(file))
    return {key.strip(): [float(row[key]) for row in rows] for key in rows[0]}


def curve_summary(results: dict[str, list[float]], epoch_limit: int, patience: int) -> dict:
    """Epochs run, best epoch, stop reason and simple under/overfitting signals."""
    fitness = results['metrics/mAP50-95(B)']
    epochs = len(fitness)
    best = int(np.argmax(fitness))
    last = slice(max(0, epochs-10), epochs)
    slope = float(np.polyfit(range(len(fitness[last])), fitness[last], 1)[0]) if epochs >= 3 else None
    train_loss, val_loss = results.get('train/box_loss'), results.get('val/box_loss')
    val_rising = bool(val_loss and epochs >= 6 and np.mean(val_loss[-3:]) > min(val_loss) * 1.05)
    train_falling = bool(train_loss and epochs >= 6 and np.mean(train_loss[-3:]) < np.mean(train_loss[-6:-3]))
    stop = 'epoch limit reached' if epochs >= epoch_limit else (
        'early stopping (no improvement for patience epochs)' if epochs - 1 - best >= patience else 'interrupted or resumed; check logs')
    return {'epochs_run': epochs, 'epoch_limit': epoch_limit, 'best_epoch': best + 1, 'best_mAP50_95': float(fitness[best]),
            'best_mAP50': float(results['metrics/mAP50(B)'][best]), 'stop_reason': stop,
            'last10_fitness_slope_per_epoch': slope,
            'still_improving_at_limit': bool(epochs >= epoch_limit and slope is not None and slope > 0 and best >= epochs - 5),
            'possible_overfitting': val_rising and train_falling,
            'next_epoch_cap': 100 if epochs >= epoch_limit and slope is not None and slope > 0 and best >= epochs - 5 else epoch_limit}


def plot_curves(results: dict[str, list[float]], output: Path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 3, figsize=(15, 4))
    epochs = range(1, len(results['metrics/mAP50-95(B)'])+1)
    for key in ('train/box_loss', 'val/box_loss', 'train/cls_loss', 'val/cls_loss'):
        if key in results:
            axes[0].plot(epochs, results[key], label=key)
    for key in ('metrics/mAP50(B)', 'metrics/mAP50-95(B)'):
        axes[1].plot(epochs, results[key], label=key)
    for key in ('metrics/precision(B)', 'metrics/recall(B)'):
        axes[2].plot(epochs, results[key], label=key)
    for axis, title in zip(axes, ('Loss', 'Validation mAP', 'Validation P/R (Ultralytics operating point)')):
        axis.set_title(title); axis.set_xlabel('epoch'); axis.legend(fontsize=8)
    figure.tight_layout(); figure.savefig(output, dpi=110); plt.close(figure)


# --- 3. Near misses and clusters (diagnostic only; never a score) --------------------

def near_miss_table(evaluation: dict, width: int = 640, height: int = 640) -> list[dict]:
    """For each label box: best overlap with any saved prediction and a failure category.

    Use an evaluation run at a low confidence (e.g. 0.05) so that weak predictions are visible.
    """
    rows = []
    for record in evaluation['per_image']:
        predictions = record['predictions']
        truths = [t['box'] for t in record['truths']]
        matched = {m['truth'] for m in record['matches']}
        for index, truth in enumerate(truths):
            overlaps = [(iou(p['box'], truth), p['confidence'], p['box']) for p in predictions]
            best_iou, best_conf, best_box = max(overlaps, default=(0.0, None, None))
            covered = sum(iou(p['box'], truth) > .1 for p in predictions)
            # A prediction spanning several labels, or several predictions inside one label.
            spans = best_box is not None and sum(iou(best_box, other) > .1 for other in truths) > 1
            if index in matched:
                category = 'matched'
            elif best_iou < .1:
                category = 'no prediction nearby'
            elif spans or covered > 1:
                category = 'cluster mismatch'
            else:
                category = 'near-miss localisation'
            side = short_side_px(truth, width, height)
            rows.append({'image': record['image'], 'truth': index, 'short_side_px': round(side, 1),
                         'size_bucket': size_bucket(side), 'tiny_under_8px': side < 8,
                         'best_iou': round(best_iou, 3), 'best_confidence': best_conf, 'category': category})
    return rows


def what_if(table: list[dict], iou_threshold: float) -> dict:
    """How many labels a looser overlap rule would reach. DIAGNOSTIC ONLY; not a result."""
    reached = sum(r['best_iou'] >= iou_threshold for r in table)
    return {'label': f'diagnostic only: labels with any prediction at IoU >= {iou_threshold}', 'reached': reached, 'labels': len(table)}


# --- 4. Overlays --------------------------------------------------------------------

def _dashed_rectangle(draw, box, colour, dash=4):
    x1, y1, x2, y2 = box
    for start in range(int(x1), int(x2), dash*2):
        draw.line([(start, y1), (min(start+dash, x2), y1)], fill=colour); draw.line([(start, y2), (min(start+dash, x2), y2)], fill=colour)
    for start in range(int(y1), int(y2), dash*2):
        draw.line([(x1, start), (x1, min(start+dash, y2))], fill=colour); draw.line([(x2, start), (x2, min(start+dash, y2))], fill=colour)


def draw_overlay(image_path: Path, record: dict, threshold: float, output: Path, companion: Path | None = None):
    """Labels green; predictions >= threshold red with confidence/IoU; weaker predictions dashed orange."""
    image = Image.open(image_path).convert('RGB')
    panels = [image] + ([Image.open(companion).convert('RGB')] if companion and companion.is_file() else [])
    rendered = []
    for panel in panels:
        panel = panel.copy(); draw = ImageDraw.Draw(panel); w, h = panel.size
        pixels = lambda b: [b[0]*w, b[1]*h, b[2]*w, b[3]*h]
        truths = [t['box'] for t in record['truths']]
        for truth in truths:
            draw.rectangle(pixels(truth), outline=(0, 230, 0), width=2)
        for prediction in record['predictions']:
            box, confidence = prediction['box'], prediction['confidence']
            overlap = max((iou(box, t) for t in truths), default=0.0)
            if confidence >= threshold:
                draw.rectangle(pixels(box), outline=(255, 40, 40), width=2)
                draw.text((pixels(box)[0], max(0, pixels(box)[1]-11)), f'{confidence:.2f} IoU {overlap:.2f}', fill=(255, 40, 40))
            else:
                _dashed_rectangle(draw, pixels(box), (255, 160, 0))
        rendered.append(panel)
    height = max(p.height for p in rendered)
    canvas = Image.new('RGB', (sum(p.width for p in rendered), height), (0, 0, 0))
    x = 0
    for panel in rendered:
        canvas.paste(panel, (x, 0)); x += panel.width
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=92)


def views_to_inspect(evaluation_at_threshold: dict, table: list[dict], per_bucket: int = 3) -> list[str]:
    """Every view with a false alarm, plus missed views stratified by label size."""
    chosen = [r['image'] for r in evaluation_at_threshold['per_image'] if r['fp'] > 0]
    missed = [r for r in table if r['category'] != 'matched']
    for bucket in ('<8', '8-16', '16-32', '>=32'):
        images = sorted({r['image'] for r in missed if r['size_bucket'] == bucket} - set(chosen))
        chosen += images[:per_bucket]
    return list(dict.fromkeys(chosen))


# --- 5. Domain statistics -----------------------------------------------------------

def laplacian_variance(gray: np.ndarray) -> float:
    if gray.shape[0] < 3 or gray.shape[1] < 3:
        return float('nan')
    g = gray.astype(np.float32)
    lap = 4*g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(lap.var())


def box_statistics(image_dir: Path, label_dir: Path, input_size: int = 640, limit: int | None = None) -> dict:
    """Label size at detector input, objects per image and sharpness inside boxes at detector scale."""
    sides, sharpness, counts = [], [], []
    paths = sorted(p for p in image_dir.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)[:limit]
    for path in paths:
        lines = [l.split() for l in (label_dir/f'{path.stem}.txt').read_text().splitlines() if l.strip()]
        counts.append(len(lines))
        if not lines:
            continue
        with Image.open(path) as image:
            scale = input_size / max(image.size)
            small = image.convert('L').resize((round(image.width*scale), round(image.height*scale)), Image.Resampling.BILINEAR)
        gray = np.asarray(small)
        for _, x, y, w, h in (map(float, l) for l in lines):
            sides.append(min(w*small.width, h*small.height))
            x1, y1 = int((x-w/2)*small.width), int((y-h/2)*small.height)
            x2, y2 = int(np.ceil((x+w/2)*small.width)), int(np.ceil((y+h/2)*small.height))
            sharpness.append(laplacian_variance(gray[max(0, y1):y2, max(0, x1):x2]))
    sides, sharp = np.array(sides), np.array([s for s in sharpness if np.isfinite(s)])
    pct = lambda a: [round(float(v), 1) for v in np.percentile(a, [10, 50, 90])] if len(a) else None
    return {'images': len(paths), 'labels': int(len(sides)), 'images_without_labels': int(sum(c == 0 for c in counts)),
            'labels_per_image_mean': round(float(np.mean(counts)), 2) if counts else None,
            'short_side_px_p10_p50_p90': pct(sides),
            'share_under_8px': round(float((sides < 8).mean()), 3) if len(sides) else None,
            'share_under_16px': round(float((sides < 16).mean()), 3) if len(sides) else None,
            'share_under_32px': round(float((sides < 32).mean()), 3) if len(sides) else None,
            'box_sharpness_p10_p50_p90': pct(sharp)}


def category_counts(table: list[dict]) -> dict:
    return {'by_category': dict(Counter(r['category'] for r in table)),
            'by_category_and_size': {f'{c} | {b}': n for (c, b), n in sorted(Counter((r['category'], r['size_bucket']) for r in table).items())}}
