"""SAM 2 segmentation via Hugging Face Inference API for waste area estimation."""
import io
import base64
import logging

import httpx
from PIL import Image
from backend.config import hf_api_token
from backend.errors import ServiceError

logger = logging.getLogger('geoclean')
HF_API_URL = "https://api-inference.huggingface.co/models/facebook/sam2-hiera-large"


def is_configured() -> bool:
    return bool(hf_api_token())


def segment(image: Image.Image, box: list[float]) -> dict:
    """Segment a detected waste region and estimate its visible area percentage.

    box: [x1, y1, x2, y2] in 0-1 normalised coordinates.
    Returns {mask_area_pct: float|None, mask_available: bool}.
    """
    token = hf_api_token()
    if not token:
        return {'mask_area_pct': None, 'mask_available': False}

    width, height = image.size
    # Convert normalised box to pixel coords
    px_box = [box[0]*width, box[1]*height, box[2]*width, box[3]*height]

    buf = io.BytesIO()
    image.save(buf, format='JPEG', quality=90)

    try:
        response = httpx.post(
            HF_API_URL,
            headers={'Authorization': f'Bearer {token}'},
            json={
                'inputs': {'image': base64.b64encode(buf.getvalue()).decode('ascii')},
                'parameters': {'input_boxes': [[px_box]]},
            },
            timeout=30,
        )
        if response.status_code >= 400:
            logger.warning('SAM2 HTTP %s (non-fatal)', response.status_code)
            return {'mask_area_pct': _estimate_from_box(box), 'mask_available': False}
        result = response.json()
    except Exception:
        logger.debug('SAM2 call failed (non-fatal), using box estimate')
        return {'mask_area_pct': _estimate_from_box(box), 'mask_available': False}

    return _parse_mask(result, box)


def _parse_mask(result, box):
    """Parse SAM2 response and compute area percentage."""
    try:
        if isinstance(result, list) and result:
            # Count mask pixels if mask data is returned
            mask_data = result[0] if isinstance(result[0], dict) else {}
            if 'mask' in mask_data:
                # Approximate area from mask
                return {'mask_area_pct': round(float(mask_data.get('area', 0)) * 100, 2), 'mask_available': True}
        return {'mask_area_pct': _estimate_from_box(box), 'mask_available': False}
    except Exception:
        return {'mask_area_pct': _estimate_from_box(box), 'mask_available': False}


def _estimate_from_box(box):
    """Rough area estimate from bounding box (percentage of image)."""
    if not box or len(box) != 4:
        return None
    w = abs(box[2] - box[0])
    h = abs(box[3] - box[1])
    return round(w * h * 100, 2)  # % of image area
