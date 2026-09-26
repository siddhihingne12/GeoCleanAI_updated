"""Tiled detection on a view rendered above the model's 640px input.

A view rendered at, say, 1024px keeps real panorama detail that a 640px render throws away.
It is cut into overlapping 640px tiles; each tile goes through the unchanged 640px model and
the boxes are mapped back to the view. With 640px tiles 384px apart the overlap is 256px, so
any object smaller than that appears whole in at least one tile. When two tiles report the
same object, a box not cut by an inner tile edge wins; otherwise the more confident one does.
Shared by the API and the evaluator so both measure exactly the same thing.
"""
from typing import Callable

import numpy as np
from PIL import Image

from backend.geometry import letterbox

TILE = 640
DUPLICATE_IOU = .5
# Intersection over the smaller box: a fragment inside a fuller box is the same object.
DUPLICATE_IOS = .8
EDGE_PX = 2


def axis_origins(extent: int, tile: int, stride: int) -> list[int]:
    if extent <= tile:
        return [0]
    origins = list(range(0, extent - tile, stride))
    return origins + [extent - tile]


def tile_grid(width: int, height: int, tile: int = TILE, stride: int = 384) -> list[tuple[int, int]]:
    return [(x, y) for y in axis_origins(height, tile, stride) for x in axis_origins(width, tile, stride)]


def _overlaps(a, b):
    inter = max(0., min(a[2], b[2]) - max(a[0], b[0])) * max(0., min(a[3], b[3]) - max(a[1], b[1]))
    area = lambda box: max(0., box[2] - box[0]) * max(0., box[3] - box[1])
    union = area(a) + area(b) - inter
    smaller = min(area(a), area(b))
    return (inter / union if union > 0 else 0.), (inter / smaller if smaller > 0 else 0.)


def merge_tile_detections(detections: list[dict]) -> list[dict]:
    """detections: {'box': face pixels [x1,y1,x2,y2], 'confidence', 'cut': touches an inner tile edge}."""
    ordered = sorted(detections, key=lambda d: (d['cut'], -d['confidence']))
    kept = []
    for candidate in ordered:
        if not any(max(_overlaps(candidate['box'], k['box'])[0] >= DUPLICATE_IOU,
                       _overlaps(candidate['box'], k['box'])[1] >= DUPLICATE_IOS) for k in kept):
            kept.append(candidate)
    return sorted(kept, key=lambda d: -d['confidence'])


def detect_view(image: Image.Image, run: Callable, threshold: float, tile: int = TILE, stride: int = 384) -> list[tuple[list[float], float]]:
    """run(tensor) -> rows [x1,y1,x2,y2,conf,cls] in letterboxed tile pixels.

    Returns (normalized view box, confidence) pairs, most confident first.
    """
    width, height = image.size
    found = []
    for x0, y0 in tile_grid(width, height, tile, stride):
        crop = image.crop((x0, y0, min(x0 + tile, width), min(y0 + tile, height)))
        tensor, scale, left, top = letterbox(crop, tile)
        rows = np.asarray(run(tensor)).reshape(-1, 6)
        for x1, y1, x2, y2, confidence, label in rows:
            if not np.isfinite([x1, y1, x2, y2, confidence]).all() or confidence < threshold or confidence > 1 or label != 0:
                continue
            # Letterboxed tile pixels -> tile pixels, clipped to the tile's real content.
            bx1, bx2 = (float(np.clip((v - left) / scale, 0, crop.width)) for v in (x1, x2))
            by1, by2 = (float(np.clip((v - top) / scale, 0, crop.height)) for v in (y1, y2))
            if bx2 <= bx1 or by2 <= by1:
                continue
            inner_edges = [(bx1, x0 > 0), (by1, y0 > 0), (crop.width - bx2, x0 + crop.width < width), (crop.height - by2, y0 + crop.height < height)]
            cut = any(is_inner and gap <= EDGE_PX for gap, is_inner in inner_edges)
            found.append({'box': [bx1 + x0, by1 + y0, bx2 + x0, by2 + y0], 'confidence': float(confidence), 'cut': cut})
    merged = merge_tile_detections(found)
    return [([d['box'][0] / width, d['box'][1] / height, d['box'][2] / width, d['box'][3] / height], d['confidence']) for d in merged]
