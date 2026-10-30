"""Unified AI service combining Grounding DINO + SAM 2 + Roboflow + ONNX detectors."""
import logging
import uuid

from PIL import Image
from backend.config import WASTE_PROMPTS
from backend.errors import ServiceError
from backend.geometry import point_to_basic
from backend.schemas import ViewSpec

logger = logging.getLogger('geoclean')


def _severity(confidence: float, area_pct: float | None = None) -> str:
    if confidence >= 0.7 or (area_pct and area_pct > 5):
        return 'high'
    if confidence >= 0.5 or (area_pct and area_pct > 2):
        return 'medium'
    return 'low'


def detect_waste(image: Image.Image, view: ViewSpec, image_id: str,
                 lat: float = 0, lng: float = 0) -> list[dict]:
    """Run the full AI detection pipeline.

    Priority: Grounding DINO → Roboflow → Local ONNX.
    Each detection gets optional SAM 2 segmentation for area estimation.
    Results are saved to the database.
    """
    detections = []
    model_used = 'unknown'

    # ── Try Grounding DINO first ──
    try:
        from backend import grounding_dino
        if grounding_dino.is_configured():
            raw = grounding_dino.detect(image, WASTE_PROMPTS, threshold=0.3)
            model_used = 'grounding-dino'
            detections = raw
            logger.info('Grounding DINO found %d candidates', len(raw))
    except ServiceError:
        logger.info('Grounding DINO unavailable, trying fallbacks')
    except Exception:
        logger.exception('Grounding DINO error')

    # ── Fallback to Roboflow ──
    if not detections:
        try:
            from backend import roboflow_detector
            if roboflow_detector.is_configured():
                detections = roboflow_detector.detect(image, view, confidence_threshold=0.35)
                model_used = 'roboflow'
                logger.info('Roboflow found %d candidates', len(detections))
        except Exception:
            logger.exception('Roboflow fallback error')

    # ── Last fallback: local ONNX ──
    if not detections:
        try:
            from backend import detector
            info = detector.manifest()
            if info.get('format') != 'roboflow-workflow':
                detections = detector.detect(image, view, info)
                model_used = 'yolo-onnx'
                logger.info('Local ONNX found %d candidates', len(detections))
        except Exception:
            logger.debug('Local ONNX not available')

    # ── Enrich with SAM 2 segmentation ──
    enriched = []
    for i, det in enumerate(detections):
        area_pct = None
        try:
            from backend import sam2_segmenter
            if sam2_segmenter.is_configured() and 'box' in det:
                seg = sam2_segmenter.segment(image, det['box'])
                area_pct = seg.get('mask_area_pct')
        except Exception:
            pass
        if area_pct is None and 'box' in det:
            b = det['box']
            area_pct = round(abs(b[2] - b[0]) * abs(b[3] - b[1]) * 100, 2)

        severity = _severity(det.get('confidence', 0), area_pct)

        box = det.get('box', [0, 0, 0, 0])
        tag = det.get('tag')
        if not tag and box:
            try:
                tag = point_to_basic((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, view)
            except Exception:
                tag = [0.5, 0.5]

        enriched.append({
            'id': det.get('id', f'waste-{i+1}'),
            'label': det.get('label', 'waste'),
            'confidence': det.get('confidence', 0),
            'box': box,
            'tag': tag,
            'severity': severity,
            'waste_area_pct': area_pct,
            'model_used': model_used,
        })

    # ── Save to database ──
    try:
        from backend import database
        for det in enriched:
            database.save_detection(
                det_id=f'{image_id}-{det["id"]}-{uuid.uuid4().hex[:6]}',
                image_id=image_id, lat=lat, lng=lng,
                label=det['label'], confidence=det['confidence'],
                box=det['box'], severity=det['severity'],
                waste_area_pct=det.get('waste_area_pct'),
                model_used=model_used,
                view_id=det.get('view_id'),
            )
    except Exception:
        logger.debug('Could not save detections to database', exc_info=True)

    # ── Update hotspots ──
    try:
        from backend import hotspot_engine
        hotspot_engine.update_hotspots()
    except Exception:
        logger.debug('Hotspot update failed', exc_info=True)

    return enriched
