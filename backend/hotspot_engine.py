"""Hotspot analysis engine — clusters nearby detections and computes priority scores."""
import math
import logging
import time
from backend import database

logger = logging.getLogger('geoclean')
CLUSTER_RADIUS_M = 100
WEIGHTS = {'area': 0.3, 'observations': 0.25, 'confidence': 0.2, 'recency': 0.15, 'repeat': 0.1}


def _haversine(lat1, lng1, lat2, lng2):
    R = 6_371_000
    a, b = math.radians(lat1), math.radians(lat2)
    h = math.sin((b - a) / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return R * 2 * math.asin(math.sqrt(min(1, h)))


def _cluster(detections):
    clusters, used = [], set()
    for i, det in enumerate(detections):
        if i in used:
            continue
        cluster = [det]
        used.add(i)
        for j, other in enumerate(detections):
            if j in used:
                continue
            if _haversine(det['lat'], det['lng'], other['lat'], other['lng']) <= CLUSTER_RADIUS_M:
                cluster.append(other)
                used.add(j)
        clusters.append(cluster)
    return clusters


def _score(cluster):
    now = time.time()
    count = len(cluster)
    avg_conf = sum(d.get('confidence', 0) for d in cluster) / max(count, 1)
    max_waste = max((d.get('waste_area_pct') or 0) for d in cluster)
    newest = max((d.get('detected_at', 0) for d in cluster), default=0)
    unique = len(set(d.get('image_id', '') for d in cluster))
    age = (now - newest) / 86400 if newest else 90
    return (WEIGHTS['area'] * min(max_waste / 20, 1) +
            WEIGHTS['observations'] * min(count / 20, 1) +
            WEIGHTS['confidence'] * avg_conf +
            WEIGHTS['recency'] * max(0, 1 - age / 90) +
            WEIGHTS['repeat'] * min(unique / 5, 1))


def update_hotspots():
    dets = database.get_detections(limit=2000)
    if not dets:
        return
    for i, cluster in enumerate(_cluster(dets)):
        if not cluster:
            continue
        avg_lat = sum(d['lat'] for d in cluster) / len(cluster)
        avg_lng = sum(d['lng'] for d in cluster) / len(cluster)
        s = _score(cluster)
        avg_conf = sum(d.get('confidence', 0) for d in cluster) / len(cluster)
        priority = 'high' if s > 0.7 else 'medium' if s > 0.4 else 'low'
        database.save_hotspot(
            hs_id=f'hotspot-{i+1}', lat=round(avg_lat, 6), lng=round(avg_lng, 6),
            priority=priority, score=s, detection_count=len(cluster),
            avg_confidence=avg_conf,
            description=f'{len(cluster)} waste observations near ({avg_lat:.4f}, {avg_lng:.4f})',
        )
    logger.info('Updated %d hotspots from %d detections', len(_cluster(dets)), len(dets))


def get_nearby_hotspot(lat, lng, radius_m=100):
    for hs in database.get_hotspots():
        if _haversine(lat, lng, hs['lat'], hs['lng']) <= radius_m:
            return hs
    return None
