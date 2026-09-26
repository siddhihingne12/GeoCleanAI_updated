"""Export the same six perspective views used by live panorama analysis.

These are annotation candidates only. No empty labels are created because an
empty label means a human verified the view contains no litter.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

from backend.geometry import perspective
from backend.panorama import ANALYSIS_VERSION, panorama_views


def export(manifest: Path, output: Path, limit: int | None = None) -> dict:
    candidates = json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(candidates, list):
        raise ValueError('Expected a list of panorama candidates')
    if any((output / 'reviews').glob('*.json')):
        raise ValueError('This folder has human reviews. Export changed images to a new folder.')
    output.mkdir(parents=True, exist_ok=True)
    image_dir = output / 'images'
    image_dir.mkdir(exist_ok=True)
    records = []
    for candidate in candidates[:limit]:
        image_id = str(candidate['id'])
        source = Path(candidate['path'])
        original = Path('artifacts') / f'panorama-{image_id}.jpg'
        if original.is_file():
            source = original
        if not source.is_file():
            raise FileNotFoundError(source)
        captured = datetime.fromtimestamp(candidate['captured_at'] / 1000, timezone.utc).date().isoformat()
        with Image.open(source) as panorama:
            size = list(panorama.size)
            if size[0] != 2 * size[1]:
                raise ValueError(f'{source} is not a 2:1 panorama')
            for view_id, view in panorama_views():
                name = f'{image_id}_{view_id}.jpg'
                perspective(panorama, view).save(image_dir / name, format='JPEG', quality=92)
                records.append({
                    'file_name': name, 'image_id': image_id, 'view_id': view_id,
                    'capture_date': captured, 'contributor': candidate['creator'],
                    'source_url': candidate['source_url'], 'panorama_size': size,
                    'sequence': candidate.get('sequence'),
                    'source_file': str(source), 'original_resolution': source == original,
                    'review_status': 'unreviewed',
                })
    result = {'analysis_version': ANALYSIS_VERSION, 'views': records,
              'notice': 'Annotation candidates only. Missing labels are unreviewed, not clean.'}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return {'panoramas': len(candidates[:limit]), 'views': len(records),
            'original_resolution_views': sum(row['original_resolution'] for row in records)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('artifacts/pune-review/candidates.json'))
    parser.add_argument('--output', type=Path, default=Path('data/pune-review'))
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    print(export(args.manifest, args.output, args.limit))
