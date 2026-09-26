"""Fetch original surveyed panoramas and sequence metadata before human review.

Run from the project root: python -m training.prepare_pune_review [--candidates ... --output ...]
"""
import argparse
import json
from pathlib import Path

from backend.providers import download_panorama, get_image, graph
from training.export_pune_views import export


def main(candidates_path: Path = Path('artifacts/pune-review/candidates.json'), output: Path = Path('data/pune-review')):
    if any((output / 'reviews').glob('*.json')):
        raise ValueError('Review has already started. Keep reviewed images unchanged.')
    manifest = candidates_path
    candidates = json.loads(manifest.read_text(encoding='utf-8'))
    failures = []
    for candidate in candidates:
        image_id = candidate['id']
        try:
            item, meta = get_image(image_id, original=True)
            if not item.get('thumb_original_url'):
                raise ValueError('Original panorama unavailable')
            sequence = graph(image_id, {'fields': 'sequence'})['sequence']
            if not isinstance(sequence, str) or not sequence:
                raise ValueError('Capture sequence unavailable')
            path = Path('artifacts') / f'panorama-{image_id}.jpg'
            if not path.exists():
                panorama = download_panorama(item)
                panorama.save(path, quality=95)
            candidate.update(sequence=sequence, creator=meta['creator'], captured_at=meta['captured_at'])
            print(f'{image_id}: original and capture sequence ready', flush=True)
        except Exception as error:
            failures.append({'image_id': image_id, 'error_type': type(error).__name__})
            print(f'{image_id}: unavailable ({type(error).__name__})', flush=True)
    manifest.write_text(json.dumps(candidates, indent=2), encoding='utf-8')
    manifest.with_name('preparation-report.json').write_text(json.dumps({'failures': failures}, indent=2))
    if failures:
        raise RuntimeError('Some originals or capture sequences are unavailable; see preparation-report.json')
    print(export(manifest, output), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, default=Path('artifacts/pune-review/candidates.json'))
    parser.add_argument('--output', type=Path, default=Path('data/pune-review'))
    args = parser.parse_args()
    main(args.candidates, args.output)
