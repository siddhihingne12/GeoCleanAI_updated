"""Survey Mapillary panorama candidates across Pune for manual review.

This is a bounded set of sample areas, not a complete citywide inventory.
Credentials come from .env.local and are never written to the report.
"""

import argparse
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import PUNE_BOUNDS
from backend.providers import distance_m, graph, normalize_image


AREAS = [
    ('Central Pune', 18.5204, 73.8567),
    ('Koregaon Park', 18.5362, 73.8939),
    ('Kothrud', 18.5074, 73.8077),
    ('Hadapsar', 18.5089, 73.9260),
    ('Aundh', 18.5590, 73.8070),
    ('Baner', 18.5590, 73.7860),
    ('Wakad', 18.5990, 73.7650),
    ('Viman Nagar', 18.5670, 73.9140),
    ('Kalyani Nagar', 18.5460, 73.9030),
    ('Camp', 18.5080, 73.8790),
    ('Swargate', 18.5010, 73.8590),
    ('Kondhwa', 18.4770, 73.8910),
    ('Sinhagad Road', 18.4800, 73.8400),
    ('Pimpri', 18.6200, 73.8000),
    ('Lohegaon', 18.5980, 73.9160),
]


def survey_area(name: str, lat: float, lng: float, radius_m: int) -> dict:
    dx = radius_m / (111_320 * math.cos(math.radians(lat)))
    dy = radius_m / 111_320
    west, south, east, north = PUNE_BOUNDS
    bbox = f'{max(west, lng-dx)},{max(south, lat-dy)},{min(east, lng+dx)},{min(north, lat+dy)}'
    raw = graph('images', {
        'bbox': bbox,
        'is_pano': 'true',
        'fields': 'id,geometry,captured_at,creator,is_pano',
        'limit': 100,
    })
    rows = raw.get('data', [])
    images = []
    for row in rows:
        image = normalize_image(row)
        distance = distance_m(lat, lng, image['lat'], image['lng'])
        if image['is_pano'] and distance <= radius_m:
            images.append({k: image[k] for k in ('id', 'lat', 'lng', 'captured_at', 'creator')})
    return {
        'area': name,
        'center': {'lat': lat, 'lng': lng},
        'radius_m': radius_m,
        'truncated': bool(raw.get('paging', {}).get('next')),
        'possibly_capped': len(rows) >= 100,
        'images': images,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--radius-m', type=int, default=1500)
    parser.add_argument('--output', type=Path, default=Path('artifacts/pune-survey.json'))
    args = parser.parse_args()
    if not 100 <= args.radius_m <= 2000:
        parser.error('--radius-m must be between 100 and 2000')

    areas = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(survey_area, name, lat, lng, args.radius_m): name
            for name, lat, lng in AREAS
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
                print(f'{name}: {len(result["images"])} candidate panoramas; possibly capped={result["possibly_capped"]}', flush=True)
            except Exception as error:
                result = {'area': name, 'error': getattr(error, 'code', type(error).__name__)}
                print(f'{name}: request failed ({result["error"]})', flush=True)
            areas.append(result)

    unique = {}
    for area in areas:
        for image in area.get('images', []):
            unique[image['id']] = image
    report = {
        'scope': f'{len(AREAS)} sample areas within the Pune demo bounds; not a citywide inventory',
        'radius_m': args.radius_m,
        'unique_candidate_count': len(unique),
        'areas': sorted(areas, key=lambda area: area['area']),
        'unique_candidates': sorted(unique.values(), key=lambda image: image['id']),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'{len(unique)} unique candidates. Review image quality, dates and litter before using them. Report: {args.output}')


if __name__ == '__main__':
    main()
