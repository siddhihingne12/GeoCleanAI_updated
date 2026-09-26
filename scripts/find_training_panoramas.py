"""Find Pune panoramas that are safe to label for training/validation (metadata only).

Safe means: not in any capture sequence used by the locked Pune test, and at least
--min-distance-m from every test panorama, so nearby repeated scenes cannot leak into
training. Nothing is downloaded except Mapillary metadata. Credentials come from
.env.local and are never written to the report.
"""
import argparse
import json
from datetime import datetime, timezone
import math
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import PUNE_BOUNDS
from backend.providers import distance_m, graph
from scripts.survey_pune import AREAS

FIELDS = 'id,geometry,captured_at,creator,is_pano,sequence'


def search(name: str, lat: float, lng: float, radius_m: int, limit: int) -> dict:
    dx = radius_m / (111_320 * math.cos(math.radians(lat)))
    dy = radius_m / 111_320
    west, south, east, north = PUNE_BOUNDS
    bbox = f'{max(west, lng-dx)},{max(south, lat-dy)},{min(east, lng+dx)},{min(north, lat+dy)}'
    rows = graph('images', {'bbox': bbox, 'is_pano': 'true', 'fields': FIELDS, 'limit': limit}).get('data', [])
    images = []
    for row in rows:
        coords = (row.get('geometry') or {}).get('coordinates', [])
        if len(coords) == 2 and row.get('is_pano'):
            images.append({'id': str(row['id']), 'lng': coords[0], 'lat': coords[1], 'captured_at': row.get('captured_at') or 0,
                           'creator': (row.get('creator') or {}).get('username', 'unknown'), 'sequence': row.get('sequence')})
    return {'area': name, 'returned': len(rows), 'possibly_capped': len(rows) >= limit, 'images': images}


def search_with_retry(name, lat, lng, radius_m, limit):
    """Dense areas sometimes time out at Mapillary; retry with smaller pages (results may then be capped)."""
    for size in dict.fromkeys((limit, 200, 50)):
        try:
            return search(name, lat, lng, radius_m, size)
        except Exception as error:
            last = error
    raise last


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--radius-m', type=int, default=1500)
    parser.add_argument('--limit', type=int, default=1000)
    parser.add_argument('--min-distance-m', type=int, default=300)
    parser.add_argument('--test-manifest', type=Path, default=Path('data/pune-test-v1/manifest.json'))
    parser.add_argument('--survey', type=Path, default=Path('artifacts/pune-survey.json'))
    parser.add_argument('--review-manifest', type=Path, default=Path('data/pune-review/manifest.json'), help='Views reviewed for the test set (kept or skipped)')
    parser.add_argument('--output', type=Path, default=Path('artifacts/pune-training-candidates.json'))
    parser.add_argument('--grid-km', type=float, help='Search a grid over the whole Pune demo area at this spacing instead of the 15 sample areas')
    args = parser.parse_args()
    areas = AREAS
    if args.grid_km:
        west, south, east, north = PUNE_BOUNDS
        step_lat = args.grid_km / 111.32
        step_lng = args.grid_km / (111.32 * math.cos(math.radians((south + north) / 2)))
        areas = [(f'grid {lat:.3f},{lng:.3f}', lat, lng)
                 for lat in [south + step_lat * (i + .5) for i in range(int((north - south) / step_lat))]
                 for lng in [west + step_lng * (j + .5) for j in range(int((east - west) / step_lng))]]

    test_views = json.loads(args.test_manifest.read_text())['views']
    test_sequences = {v['sequence'] for v in test_views}
    test_ids = {v['image_id'] for v in test_views}
    # Every panorama reviewed for the test (kept or skipped) counts as a test location, conservatively.
    # Training batches are not test locations, so their downloaded originals are not counted.
    review_ids = test_ids | {v['image_id'] for v in json.loads(args.review_manifest.read_text())['views']}
    known = {c['id']: c for c in json.loads(args.survey.read_text())['unique_candidates']}
    test_points = [(known[i]['lat'], known[i]['lng']) for i in review_ids if i in known]
    missing = sorted(review_ids - set(known))

    area_reports, found = [], {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(search_with_retry, name, lat, lng, args.radius_m, args.limit): name for name, lat, lng in areas}
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as error:
                result = {'area': futures[future], 'error': getattr(error, 'code', type(error).__name__), 'images': []}
            area_reports.append({k: v for k, v in result.items() if k != 'images'})
            for image in result['images']:
                found[image['id']] = image
            print(f"{result['area']}: {len(result['images'])} panoramas{' (capped)' if result.get('possibly_capped') else ''}{' ERROR ' + result['error'] if 'error' in result else ''}", flush=True)

    safe, excluded = [], defaultdict(int)
    for image in found.values():
        nearest = min((distance_m(image['lat'], image['lng'], lat, lng) for lat, lng in test_points), default=None)
        image['nearest_test_m'] = nearest
        if image['id'] in review_ids:
            excluded['already reviewed'] += 1
        elif image['sequence'] in test_sequences:
            excluded['test sequence'] += 1
        elif nearest is not None and nearest < args.min_distance_m:
            excluded[f'within {args.min_distance_m} m of a test panorama'] += 1
        else:
            safe.append(image)
    by_sequence = defaultdict(list)
    for image in safe:
        by_sequence[image['sequence']].append(image)
    sequences = sorted(({'sequence': s, 'panoramas': len(v), 'creator': v[0]['creator'],
                         'years': sorted({datetime.fromtimestamp(i['captured_at']/1000, timezone.utc).year for i in v if i['captured_at']})}
                        for s, v in by_sequence.items()), key=lambda r: -r['panoramas'])
    report = {'scope': f'{len(areas)} search areas, radius {args.radius_m} m; not a citywide inventory',
              'rules': {'excluded_test_sequences': sorted(test_sequences), 'min_distance_m_from_reviewed_panoramas': args.min_distance_m},
              'reviewed_locations_without_coordinates': missing,
              'areas': sorted(area_reports, key=lambda a: a['area']), 'found': len(found), 'excluded': dict(excluded),
              'safe': len(safe), 'safe_sequences': len(by_sequence), 'sequences': sequences,
              'candidates': sorted(safe, key=lambda i: (i['sequence'] or '', i['captured_at']))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('found', 'excluded', 'safe', 'safe_sequences', 'reviewed_locations_without_coordinates')}, indent=2))


if __name__ == '__main__':
    main()
