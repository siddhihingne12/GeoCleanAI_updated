import numpy as np
import pytest
from PIL import Image

from training.diagnose import (box_statistics, curve_summary, draw_overlay, laplacian_variance, near_miss_table,
                               pairing_report, views_to_inspect, what_if)


def record(image, predictions, truths, matches=()):
    return {'image': image, 'fp': 0, 'predictions': [{'box': b, 'confidence': c} for b, c in predictions],
            'truths': [{'box': b} for b in truths], 'matches': [{'truth': t} for t in matches]}


def test_near_miss_categories():
    evaluation = {'per_image': [
        record('a', [([0, 0, .1, .1], .9)], [[0, 0, .1, .1]], matches=[0]),
        record('b', [], [[.5, .5, .51, .51]]),
        record('c', [([.2, .2, .3, .3], .2)], [[.22, .2, .32, .3]]),
        # One prediction covering two neighbouring labels.
        record('d', [([.4, .4, .6, .5], .5)], [[.4, .4, .5, .5], [.5, .4, .6, .5]]),
    ]}
    table = near_miss_table(evaluation)
    assert [r['category'] for r in table] == ['matched', 'no prediction nearby', 'near-miss localisation',
                                              'cluster mismatch', 'cluster mismatch']
    assert table[1]['tiny_under_8px'] and table[1]['size_bucket'] == '<8'
    looser = what_if(table, .3)
    assert looser['label'].startswith('diagnostic only') and looser['labels'] == 5


def test_curve_summary_detects_stop_reason_and_undertraining():
    rising = [i / 100 for i in range(50)]
    results = {'metrics/mAP50-95(B)': rising, 'metrics/mAP50(B)': rising}
    summary = curve_summary(results, epoch_limit=50, patience=10)
    assert summary['epochs_run'] == 50 and summary['stop_reason'] == 'epoch limit reached'
    assert summary['still_improving_at_limit'] and summary['next_epoch_cap'] == 100
    plateau = [.3] * 5 + [.2] * 11
    stopped = curve_summary({'metrics/mAP50-95(B)': plateau, 'metrics/mAP50(B)': plateau}, 50, 10)
    assert stopped['best_epoch'] == 1 and stopped['stop_reason'].startswith('early stopping')
    assert stopped['next_epoch_cap'] == 50


def test_pairing_report_flags_missing_and_invalid_labels(tmp_path):
    for split in ('train',):
        (tmp_path/'images'/split).mkdir(parents=True); (tmp_path/'labels'/split).mkdir(parents=True)
    for name in ('a', 'b'):
        Image.new('RGB', (10, 10)).save(tmp_path/'images/train'/f'{name}.jpg')
    (tmp_path/'labels/train/a.txt').write_text('0 .5 .5 .2 .2\n1 .5 .5 .2 .2\n0 .95 .5 .2 .2\n0 .5\n')
    report = pairing_report(tmp_path, splits=('train',))['train']
    assert report['images_without_label'] == ['b']
    assert report['invalid_count'] == 3


def test_sharpness_and_box_statistics(tmp_path):
    assert laplacian_variance(np.full((10, 10), 7)) == 0
    assert laplacian_variance(np.indices((10, 10)).sum(0) % 2 * 255) > 0
    (tmp_path/'images').mkdir(); (tmp_path/'labels').mkdir()
    Image.new('RGB', (1280, 640)).save(tmp_path/'images/a.jpg')
    (tmp_path/'labels/a.txt').write_text('0 .5 .5 .01 .5\n')
    Image.new('RGB', (640, 640)).save(tmp_path/'images/b.jpg')
    (tmp_path/'labels/b.txt').write_text('')
    stats = box_statistics(tmp_path/'images', tmp_path/'labels')
    assert stats['labels'] == 1 and stats['images_without_labels'] == 1
    assert stats['short_side_px_p10_p50_p90'][1] == pytest.approx(6.4, abs=.1)
    assert stats['share_under_8px'] == 1


def test_overlay_and_inspection_list(tmp_path):
    Image.new('RGB', (640, 640)).save(tmp_path/'v.jpg')
    Image.new('RGB', (1024, 1024)).save(tmp_path/'v-1024.jpg')
    rec = record('v', [([.1, .1, .2, .2], .9), ([.5, .5, .6, .6], .1)], [[.1, .1, .2, .2]])
    draw_overlay(tmp_path/'v.jpg', rec, .35, tmp_path/'out/v.png', companion=tmp_path/'v-1024.jpg')
    output = Image.open(tmp_path/'out/v.png')
    assert output.size == (1664, 1024)
    assert output.getpixel((64, 64)) == (255, 40, 40)  # Confident prediction drawn over its label.
    assert output.getpixel((320, 320)) == (255, 160, 0)  # Weak prediction: dashed orange.
    assert output.getpixel((640 + 103, 103)) == (255, 40, 40)  # Same box scaled onto the 1024 companion.
    at_threshold = {'per_image': [{'image': 'x', 'fp': 2}, {'image': 'y', 'fp': 0}]}
    table = [{'image': 'y', 'category': 'no prediction nearby', 'size_bucket': '<8'},
             {'image': 'z', 'category': 'matched', 'size_bucket': '<8'}]
    assert views_to_inspect(at_threshold, table) == ['x', 'y']
