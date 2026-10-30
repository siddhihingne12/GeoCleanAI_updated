"""Roboflow workflow-based waste detector.

Replicates the exact behaviour of:
    client = InferenceHTTPClient(
        api_url="https://serverless.roboflow.com",
        api_key=API_KEY
    ).configure(InferenceConfiguration(api_key_transport="header"))

    client.run_workflow(
        workspace_name=WORKSPACE,
        workflow_id=WORKFLOW_ID,
        images={"image": image_path},
        use_cache=True
    )

inference-sdk is not used directly because it does not yet support Python 3.14.
The HTTP behaviour it produces is replicated here using httpx so the rest of the
pipeline (panorama merging, caching, frontend) works unchanged.
"""
from __future__ import annotations

import io
import base64
import logging

import httpx
from PIL import Image

from backend.config import roboflow_api_key, roboflow_workspace, roboflow_workflow_id
from backend.errors import ServiceError
from backend.geometry import point_to_basic
from backend.schemas import ViewSpec

logger = logging.getLogger('geoclean')

# Matches InferenceHTTPClient(api_url=...)
ROBOFLOW_API_URL = 'https://serverless.roboflow.com'


def is_configured() -> bool:
    """Return True when Roboflow credentials are present."""
    return bool(roboflow_api_key())


def _image_to_base64(image: Image.Image) -> str:
    """Encode a PIL image as a base64 JPEG string (same as inference-sdk)."""
    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=90)
    return base64.b64encode(buf.getvalue()).decode('ascii')


def detect(image: Image.Image, view: ViewSpec, confidence_threshold: float = 0.35) -> list[dict]:
    """Run the Roboflow workflow and return normalised detections.

    Replicates inference-sdk run_workflow() with api_key_transport='header'
    (inference v1.5.0+ style). The API key is sent in the Authorization header
    rather than in the JSON body.

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
    workflow  = roboflow_workflow_id()

    # Exact URL used by inference-sdk run_workflow()
    url = f'{ROBOFLOW_API_URL}/infer/workflows/{workspace}/{workflow}'

    img_b64 = _image_to_base64(image)

    # Payload mirrors inference-sdk:
    #   images={"image": <path>}  → {"image": {"type": "base64", "value": <b64>}}
    #   use_cache=True            → "enable_cache": True
    payload = {
        'inputs': {
            'image': {
                'type': 'base64',
                'value': img_b64,
            },
        },
        'enable_cache': True,
    }

    # api_key_transport='header' → Authorization: Bearer <key>
    # The api_key is NOT placed in the JSON body.
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 401:
            raise ServiceError('roboflow_auth_failed',
                               'Roboflow API key is invalid. Check ROBOFLOW_API_KEY.', 502)
        if response.status_code == 429:
            raise ServiceError('roboflow_rate_limit',
                               'Roboflow rate limit reached. Try again shortly.', 429, 10)
        if response.status_code == 404:
            logger.error('Roboflow 404 — check workspace/workflow ID. URL: %s', url)
            raise ServiceError('roboflow_request_failed',
                               'Waste detection model not found. Check your Roboflow workflow ID.', 502)
        if response.status_code >= 400:
            logger.error('Roboflow HTTP %s: %s', response.status_code, response.text[:500])
            raise ServiceError('roboflow_request_failed',
                               f'Waste detection service error (HTTP {response.status_code}). Please retry.', 502)
        result = response.json()
    except ServiceError:
        raise
    except Exception as exc:
        logger.exception('Roboflow workflow call failed')
        raise ServiceError(
            'roboflow_inference_failed',
            f'Roboflow inference failed: {exc}',
        ) from None

    logger.info('Roboflow raw response keys: %s',
                list(result.keys()) if isinstance(result, dict) else type(result).__name__)
    return _parse_workflow_result(result, image, view, confidence_threshold)


# ---------------------------------------------------------------------------
# Response parsing — mirrors how inference-sdk surfaces run_workflow() output
# ---------------------------------------------------------------------------

def _parse_workflow_result(
    result: list | dict,
    image: Image.Image,
    view: ViewSpec,
    threshold: float,
) -> list[dict]:
    """Convert the Roboflow workflow response into the app's detection format.

    inference-sdk run_workflow() returns:
        [{"predictions": {"predictions": [...], "image": {...}}, "inference_id": ..., ...}]

    This is the 'outputs' list from the raw HTTP response wrapped by the SDK.
    """
    detections: list[dict] = []
    width, height = image.size

    # The raw HTTP response is {"outputs": [...], "profiler_trace": [...]}
    # inference-sdk exposes result["outputs"] directly as the return value.
    if isinstance(result, dict) and 'outputs' in result:
        entries = result['outputs']
    elif isinstance(result, list):
        entries = result
    else:
        entries = [result]

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        predictions = _extract_predictions(entry)
        for pred in predictions:
            confidence = float(pred.get('confidence', 0))
            if confidence < threshold:
                continue
            box = _normalize_box(pred, width, height)
            if box is None:
                continue
            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                continue
            label = str(pred.get('class', pred.get('label', 'garbage'))).lower()
            detections.append({
                'id': f'waste-{len(detections) + 1}',
                'label': label,
                'confidence': round(confidence, 4),
                'box': [x1, y1, x2, y2],
                'tag': point_to_basic((x1 + x2) / 2, (y1 + y2) / 2, view),
            })
            if len(detections) >= 100:
                break

    # Sort by confidence descending
    detections.sort(key=lambda d: -d['confidence'])
    for i, d in enumerate(detections):
        d['id'] = f'waste-{i + 1}'

    return detections


def _extract_predictions(entry: dict) -> list[dict]:
    """Pull prediction dicts from a workflow output entry.

    Handles the output structure produced by the garbage_best-t8vwm workflow:
    {
        "predictions": {
            "image": {"width": ..., "height": ...},
            "predictions": [{"x":..,"y":..,"width":..,"height":..,"confidence":..,"class":..}, ...]
        },
        "inference_id": "...",
        "model_id": "..."
    }
    """
    # Primary path: Roboflow workflow → "predictions" key is a dict with inner "predictions" list
    if 'predictions' in entry:
        outer = entry['predictions']
        if isinstance(outer, dict) and 'predictions' in outer:
            inner = outer['predictions']
            if isinstance(inner, list):
                return inner
        # Flat list of predictions
        if isinstance(outer, list):
            return outer

    # Fallback: search all dict values
    for key, value in entry.items():
        if isinstance(value, dict) and 'predictions' in value:
            preds = value['predictions']
            if isinstance(preds, list):
                return preds
        if isinstance(value, list) and value and isinstance(value[0], dict):
            if 'confidence' in value[0] or 'class' in value[0]:
                return value

    return []


def _normalize_box(pred: dict, img_width: int, img_height: int) -> list[float] | None:
    """Convert a Roboflow prediction box to [x1, y1, x2, y2] in 0-1 coordinates.

    Roboflow returns center-x, center-y, width, height in pixel coordinates.
    """
    # Format 1 (Roboflow default): cx, cy, w, h in pixels
    if all(k in pred for k in ('x', 'y', 'width', 'height')):
        cx = float(pred['x'])
        cy = float(pred['y'])
        w  = float(pred['width'])
        h  = float(pred['height'])
        x1 = max(0.0, (cx - w / 2) / img_width)
        y1 = max(0.0, (cy - h / 2) / img_height)
        x2 = min(1.0, (cx + w / 2) / img_width)
        y2 = min(1.0, (cy + h / 2) / img_height)
        return [x1, y1, x2, y2]

    # Format 2: corner coordinates in pixels
    if all(k in pred for k in ('x1', 'y1', 'x2', 'y2')):
        return [
            max(0.0, float(pred['x1']) / img_width),
            max(0.0, float(pred['y1']) / img_height),
            min(1.0, float(pred['x2']) / img_width),
            min(1.0, float(pred['y2']) / img_height),
        ]

    # Format 3: already-normalised [x1, y1, x2, y2] array
    if 'bbox' in pred:
        bbox = pred['bbox']
        if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
            return [max(0.0, float(v)) for v in bbox[:2]] + [min(1.0, float(v)) for v in bbox[2:]]

    return None
