"""Roboflow workflow-based litter detector.

Calls the Roboflow serverless inference API with the trained
garbage_best-t8vwm workflow using direct HTTP requests (no SDK needed).
Returns detections in the same format as the local ONNX detector so
the rest of the pipeline (panorama merging, caching, frontend) works
unchanged.
"""
import io
import logging
import base64

import httpx
from PIL import Image

from backend.config import roboflow_api_key, roboflow_workspace, roboflow_workflow_id
from backend.errors import ServiceError
from backend.geometry import point_to_basic
from backend.schemas import ViewSpec

logger = logging.getLogger('geoclean')

ROBOFLOW_API_URL = 'https://serverless.roboflow.com'


def is_configured() -> bool:
    """Return True when Roboflow credentials are present."""
    return bool(roboflow_api_key())


def _image_to_base64(image: Image.Image) -> str:
    """Encode a PIL image as a base64 JPEG string."""
    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=90)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def detect(image: Image.Image, view: ViewSpec, confidence_threshold: float = 0.35) -> list[dict]:
    """Run detection via the Roboflow workflow HTTP API and return normalised results.

    Each result has: id, label, confidence, box [x1,y1,x2,y2] in 0-1
    normalised coordinates, and tag (equirectangular basic coordinates).
    """
    api_key = roboflow_api_key()
    if not api_key:
        raise ServiceError(
            'roboflow_not_configured',
            'Set ROBOFLOW_API_KEY in .env.local to enable Roboflow detection.',
        )

    workspace = roboflow_workspace()
    workflow = roboflow_workflow_id()
    url = f'{ROBOFLOW_API_URL}/infer/workflows/{workspace}/{workflow}'

    img_b64 = _image_to_base64(image)

    payload = {
        'api_key': api_key,
        'inputs': {
            'image': {
                'type': 'base64',
                'value': img_b64,
            },
        },
        'enable_cache': True,
    }

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401:
            raise ServiceError('roboflow_auth_failed', 'Roboflow API key is invalid. Check ROBOFLOW_API_KEY.', 502)
        if response.status_code == 429:
            raise ServiceError('roboflow_rate_limit', 'Roboflow rate limit reached. Try again shortly.', 429, 10)
        if response.status_code >= 400:
            logger.error('Roboflow HTTP %s: %s', response.status_code, response.text[:500])
            raise ServiceError('roboflow_request_failed', f'Roboflow returned HTTP {response.status_code}.', 502)
        result = response.json()
    except ServiceError:
        raise
    except Exception as exc:
        logger.exception('Roboflow workflow call failed')
        raise ServiceError(
            'roboflow_inference_failed',
            f'Roboflow inference failed: {exc}',
        ) from None

    logger.info('Roboflow raw response keys: %s', list(result.keys()) if isinstance(result, dict) else type(result).__name__)
    return _parse_workflow_result(result, image, view, confidence_threshold)


def _parse_workflow_result(
    result: list | dict,
    image: Image.Image,
    view: ViewSpec,
    threshold: float,
) -> list[dict]:
    """Convert the Roboflow workflow response into the app's detection format.

    Roboflow workflows return a list of dicts, one per image. Each dict
    may contain prediction outputs keyed by their block name. We look for
    any key containing 'predictions' or iterate the known shapes.
    """
    detections: list[dict] = []
    width, height = image.size

    # result is typically a dict with 'outputs', or a list with one entry per image
    if isinstance(result, dict) and 'outputs' in result:
        entries = result['outputs']
    elif isinstance(result, list):
        entries = result
    else:
        entries = [result]

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Try to find predictions in the workflow output.
        predictions = _extract_predictions(entry)

        for pred in predictions:
            confidence = float(pred.get('confidence', 0))
            if confidence < threshold:
                continue

            # Roboflow returns bounding boxes in various formats.
            box = _normalize_box(pred, width, height)
            if box is None:
                continue

            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                continue

            label = str(pred.get('class', pred.get('label', 'litter'))).lower()

            detections.append({
                'id': f'litter-{len(detections) + 1}',
                'label': label,
                'confidence': round(confidence, 4),
                'box': [x1, y1, x2, y2],
                'tag': point_to_basic((x1 + x2) / 2, (y1 + y2) / 2, view),
            })

            if len(detections) >= 100:
                break

    # Sort by confidence descending (consistent with local detector)
    detections.sort(key=lambda d: -d['confidence'])
    # Re-number after sort
    for i, d in enumerate(detections):
        d['id'] = f'litter-{i + 1}'

    return detections


def _extract_predictions(entry: dict) -> list[dict]:
    """Pull prediction dicts from a workflow result entry."""
    # Direct 'predictions' key (list of prediction dicts)
    if 'predictions' in entry and isinstance(entry['predictions'], list):
        return entry['predictions']

    # Nested inside a predictions wrapper with 'predictions' key
    if 'predictions' in entry and isinstance(entry['predictions'], dict):
        inner = entry['predictions'].get('predictions', [])
        if isinstance(inner, list):
            return inner

    # Try any key that looks like it has predictions
    for key, value in entry.items():
        if isinstance(value, dict) and 'predictions' in value:
            preds = value['predictions']
            if isinstance(preds, list):
                return preds
        if isinstance(value, list) and value and isinstance(value[0], dict):
            # Check if items look like predictions (have confidence or class)
            if 'confidence' in value[0] or 'class' in value[0]:
                return value

    return []


def _normalize_box(
    pred: dict, img_width: int, img_height: int,
) -> list[float] | None:
    """Convert a prediction's bounding box to [x1, y1, x2, y2] in 0-1 coords."""
    # Format 1: center x, y, width, height (pixel coordinates) – most common Roboflow format
    if all(k in pred for k in ('x', 'y', 'width', 'height')):
        cx = float(pred['x'])
        cy = float(pred['y'])
        w = float(pred['width'])
        h = float(pred['height'])
        x1 = max(0.0, (cx - w / 2) / img_width)
        y1 = max(0.0, (cy - h / 2) / img_height)
        x2 = min(1.0, (cx + w / 2) / img_width)
        y2 = min(1.0, (cy + h / 2) / img_height)
        return [x1, y1, x2, y2]

    # Format 2: corner coordinates (pixel)
    if all(k in pred for k in ('x1', 'y1', 'x2', 'y2')):
        return [
            max(0.0, float(pred['x1']) / img_width),
            max(0.0, float(pred['y1']) / img_height),
            min(1.0, float(pred['x2']) / img_width),
            min(1.0, float(pred['y2']) / img_height),
        ]

    # Format 3: already normalised bbox array
    if 'bbox' in pred:
        bbox = pred['bbox']
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return [max(0.0, float(v)) for v in bbox[:2]] + [min(1.0, float(v)) for v in bbox[2:]]

    return None
