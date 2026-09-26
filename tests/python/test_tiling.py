import numpy as np
import pytest
from PIL import Image

from backend.tiling import axis_origins, detect_view, merge_tile_detections, tile_grid


def test_grid_covers_the_view_with_overlap():
    assert axis_origins(1024, 640, 384) == [0, 384]
    assert axis_origins(640, 640, 384) == [0]
    assert axis_origins(500, 640, 384) == [0]
    assert axis_origins(1400, 640, 384) == [0, 384, 760]
    assert tile_grid(1024, 1024) == [(0, 0), (384, 0), (0, 384), (384, 384)]


def fake_model(objects):
    """Stub model that 'sees' objects (view pixels) fully or partly inside each 640px tile."""
    calls = []

    def run(tensor):
        # The evaluator passes a letterboxed 640px tile; identify the tile by the call order.
        x0, y0 = calls_grid[len(calls)]
        calls.append((x0, y0))
        rows = []
        for (x1, y1, x2, y2), confidence in objects:
            cx1, cy1, cx2, cy2 = max(x1, x0), max(y1, y0), min(x2, x0 + 640), min(y2, y0 + 640)
            if cx2 > cx1 and cy2 > cy1:
                rows.append([cx1 - x0, cy1 - y0, cx2 - x0, cy2 - y0, confidence, 0])
        return np.array(rows, dtype=np.float32).reshape(-1, 6)
    calls_grid = tile_grid(1024, 1024)
    return run, calls


def test_object_in_overlap_is_reported_once_at_view_coordinates():
    run, calls = fake_model([((500, 500, 520, 530), .9)])  # inside all four tiles
    found = detect_view(Image.new('RGB', (1024, 1024)), run, .35)
    assert len(calls) == 4 and len(found) == 1
    box, confidence = found[0]
    assert np.array(box) * 1024 == pytest.approx([500, 500, 520, 530], abs=1e-3)
    assert confidence == pytest.approx(.9)


def test_object_cut_by_a_tile_edge_keeps_the_whole_box():
    # Crosses x = 640 (edge of the first tile) but lies wholly inside the second tile column.
    run, _ = fake_model([((620, 100, 700, 140), .6)])
    found = detect_view(Image.new('RGB', (1024, 1024)), run, .35)
    assert len(found) == 1
    assert np.array(found[0][0]) * 1024 == pytest.approx([620, 100, 700, 140], abs=1e-3)


def test_separate_neighbours_are_both_kept_and_threshold_applies():
    run, _ = fake_model([((100, 100, 120, 120), .8), ((130, 100, 150, 120), .7), ((900, 900, 910, 910), .2)])
    found = detect_view(Image.new('RGB', (1024, 1024)), run, .35)
    assert len(found) == 2


def test_merge_prefers_uncut_box_over_more_confident_fragment():
    fragment = {'box': [620, 100, 640, 140], 'confidence': .9, 'cut': True}
    whole = {'box': [620, 100, 700, 140], 'confidence': .6, 'cut': False}
    assert merge_tile_detections([fragment, whole]) == [whole]
