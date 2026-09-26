"""Fixed panorama views and cross-view suppression in camera coordinates."""
import math

import numpy as np

from backend.geometry import point_to_basic
from backend.schemas import ViewSpec

# Changing projection or suppression rules must invalidate saved results.
ANALYSIS_VERSION = 'cube-100-v1'


def analysis_version(info: dict) -> str:
    """Tiled analysis renders and detects differently, so it gets its own cache version."""
    tiles = info.get('tiling')
    return ANALYSIS_VERSION if not tiles else f"{ANALYSIS_VERSION}-tile{tiles['face_size']}-{tiles['tile']}s{tiles['stride']}"


def panorama_views() -> list[tuple[str, ViewSpec]]:
    # Slight overlap gives objects at face boundaries some surrounding context.
    extent = math.tan(math.radians(50))
    bases = [
        ('front', (0, 0, 1), (1, 0, 0), (0, -1, 0)),
        ('right', (1, 0, 0), (0, 0, -1), (0, -1, 0)),
        ('back', (0, 0, -1), (-1, 0, 0), (0, -1, 0)),
        ('left', (-1, 0, 0), (0, 0, 1), (0, -1, 0)),
        ('up', (0, 1, 0), (1, 0, 0), (0, 0, 1)),
        ('down', (0, -1, 0), (1, 0, 0), (0, 0, -1)),
    ]
    return [(name, ViewSpec(origin=o, right=tuple(v * extent for v in r),
                            down=tuple(v * extent for v in d), aspect=1))
            for name, o, r, d in bases]


def reproject_box(box: list[float], source: ViewSpec, target: ViewSpec):
    """Project a box perimeter into another face without longitude seam issues."""
    x1, y1, x2, y2 = box
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    perimeter = np.array([(x1, y1), (mx, y1), (x2, y1), (x2, my),
                          (x2, y2), (mx, y2), (x1, y2), (x1, my)])
    rays = (np.array(source.origin) + (2 * perimeter[:, :1] - 1) * np.array(source.right)
            + (2 * perimeter[:, 1:] - 1) * np.array(source.down))
    depth = rays @ np.array(target.origin)
    if np.any(depth <= .01):
        return None
    plane = rays / depth[:, None] - np.array(target.origin)
    right, down = np.array(target.right), np.array(target.down)
    x = (plane @ right / (right @ right) + 1) / 2
    y = (plane @ down / (down @ down) + 1) / 2
    return [max(0., float(x.min())), max(0., float(y.min())),
            min(1., float(x.max())), min(1., float(y.max()))]


def box_iou(a, b) -> float:
    intersection = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = lambda box: max(0, box[2] - box[0]) * max(0, box[3] - box[1])
    union = area(a) + area(b) - intersection
    return intersection / union if union > 0 else 0


def merge_detections(detections: list[dict], views: dict[str, ViewSpec]) -> list[dict]:
    kept = []
    for candidate in sorted(detections, key=lambda d: -d['confidence']):
        duplicate = False
        for previous in kept:
            if previous['view_id'] == candidate['view_id']:
                continue  # The end-to-end model already suppresses within each view.
            projected = reproject_box(previous['box'], views[previous['view_id']], views[candidate['view_id']])
            if projected is not None and box_iou(candidate['box'], projected) >= .45:
                duplicate = True
                break
        if not duplicate:
            # Compute from the kept box so marker and evidence always agree.
            x1, y1, x2, y2 = candidate['box']
            kept.append({**candidate, 'id': f'litter-{len(kept) + 1}',
                         'tag': point_to_basic((x1 + x2) / 2, (y1 + y2) / 2, views[candidate['view_id']])})
    return kept
