"""Grounding DINO integration via Hugging Face Inference API for text-prompted waste detection."""
import io
import base64
import logging

import httpx
from PIL import Image
from backend.config import hf_api_token
from backend.errors import ServiceError

logger = logging.getLogger('geoclean')
HF_API_URL = "https://api-inference.huggingface.co/models/IDEA-Research/grounding-dino-base"


def is_configured() -> bool:
    return bool(hf_api_token())


def detect(image: Image.Image, prompts: list[str], threshold: float = 0.3) -> list[dict]:
    """Detect waste using Grounding DINO via HuggingFace Inference API."""
    token = hf_api_token()
    if not token:
        raise ServiceError('hf_not_configured',
                           'Set HF_API_TOKEN in .env.local for Grounding DINO detection.')

    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=90)
    img_bytes = buf.getvalue()

    prompt_text = '. '.join(prompts) + '.'
    width, height = image.size

    try:
        response = httpx.post(
            HF_API_URL,
            headers={'Authorization': f'Bearer {token}'},
            json={'inputs': {'image': base64.b64encode(img_bytes).decode('ascii'), 'text': prompt_text},
                  'parameters': {'box_threshold': threshold, 'text_threshold': threshold}},
            timeout=30,
        )
        if response.status_code == 401:
            raise ServiceError('hf_auth_failed', 'HuggingFace API token is invalid.', 502)
        if response.status_code == 429:
            raise ServiceError('hf_rate_limit', 'HuggingFace rate limit. Try again shortly.', 429, 10)
        if response.status_code == 503:
            logger.warning('Grounding DINO model is loading on HuggingFace')
            raise ServiceError('model_loading', 'Grounding DINO model is loading. Retry in ~20s.', 503, 20)
        if response.status_code >= 400:
            logger.error('GDINO HTTP %s: %s', response.status_code, response.text[:500])
            raise ServiceError('gdino_failed', f'Grounding DINO returned HTTP {response.status_code}.', 502)
        result = response.json()
    except ServiceError:
        raise
    except Exception as exc:
        logger.exception('Grounding DINO call failed')
        raise ServiceError('gdino_unavailable', f'Grounding DINO error: {exc}') from None

    return _parse_result(result, width, height, threshold)


def _parse_result(result, width, height, threshold):
    detections = []
    items = result if isinstance(result, list) else [result]
    for item in items:
        if not isinstance(item, dict):
            continue
        score = float(item.get('score', item.get('confidence', 0)))
        if score < threshold:
            continue
        box = item.get('box', {})
        if isinstance(box, dict):
            x1 = max(0.0, float(box.get('xmin', 0)) / width)
            y1 = max(0.0, float(box.get('ymin', 0)) / height)
            x2 = min(1.0, float(box.get('xmax', width)) / width)
            y2 = min(1.0, float(box.get('ymax', height)) / height)
        elif isinstance(box, (list, tuple)) and len(box) == 4:
            x1, y1, x2, y2 = [float(v) for v in box]
            if x2 > 1 or y2 > 1:
                x1, y1, x2, y2 = x1/width, y1/height, x2/width, y2/height
        else:
            continue
        if x2 <= x1 or y2 <= y1:
            continue
        label = str(item.get('label', item.get('class', 'waste'))).lower()
        detections.append({'label': label, 'confidence': round(score, 4), 'box': [x1, y1, x2, y2]})
    detections.sort(key=lambda d: -d['confidence'])
    return detections[:50]
