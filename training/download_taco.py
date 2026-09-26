"""Download official TACO annotation images with resume and dimension checks.

Reads only reviewed annotations.json. The photos are saved under their official
batch/file paths so prepare_dataset.py can verify boxes against their dimensions.
Image licences must still be reviewed before distributing a prepared dataset.
"""

import argparse
import io
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 40_000_000
MAX_BYTES = 24 * 1024 * 1024


def save_image(item: dict, root: Path) -> str:
    relative = Path(item['file_name'])
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or target.suffix.lower() != '.jpg':
        raise ValueError('Unsafe or unexpected TACO file path')
    expected = (item['width'], item['height'])
    if target.exists():
        try:
            with Image.open(target) as image:
                if image.size == expected:
                    return 'already_present'
        except (OSError, UnidentifiedImageError):
            pass

    url = item['flickr_url']
    parsed = urlparse(url)
    host = parsed.hostname or ''
    approved_host = host.endswith('.staticflickr.com') or host == 'olm-s3.s3.eu-west-1.amazonaws.com'
    if parsed.scheme != 'https' or not approved_host:
        raise ValueError('Unexpected image host')
    last_error = None
    for attempt in range(3):
        try:
            with httpx.stream('GET', url, timeout=30, follow_redirects=True) as response:
                response.raise_for_status()
                content = bytearray()
                for block in response.iter_bytes():
                    content.extend(block)
                    if len(content) > MAX_BYTES:
                        raise ValueError('Image exceeds download limit')
            with Image.open(io.BytesIO(content)) as image:
                image.load()
                # TACO dimensions describe displayed orientation; originals may
                # store portrait rotation in EXIF instead of pixel order.
                image = ImageOps.exif_transpose(image)
                if image.size != expected:
                    raise ValueError(f'Image dimensions {image.size} differ from annotations {expected}')
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix('.partial')
                image.convert('RGB').save(temporary, format='JPEG', quality=92)
                temporary.replace(target)
            return 'downloaded'
        except (httpx.HTTPError, OSError, UnidentifiedImageError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(type(last_error).__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, default=Path('data/TACO/annotations.json'))
    parser.add_argument('--images', type=Path, default=Path('data/TACO'))
    parser.add_argument('--workers', type=int, default=3)
    parser.add_argument('--max-images', type=int, help='Download only the first N images for a small verification run')
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error('--workers must be between 1 and 6')
    if args.max_images is not None and args.max_images < 1:
        parser.error('--max-images must be positive')
    data = json.loads(args.annotations.read_text(encoding='utf-8'))
    items = data['images'][:args.max_images]
    counts = {'downloaded': 0, 'already_present': 0, 'failed': 0}
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(save_image, item, args.images): item for item in items}
        for completed, future in enumerate(as_completed(futures), 1):
            item = futures[future]
            try:
                counts[future.result()] += 1
            except Exception as error:
                counts['failed'] += 1
                failures.append({'id': item['id'], 'file_name': item['file_name'], 'error': str(error)})
            if completed % 50 == 0 or completed == len(items):
                print(f'{completed}/{len(items)}: {counts}', flush=True)
    report = {'annotation_file': str(args.annotations), 'attempted': len(items), **counts, 'failures': failures}
    path = args.images / 'download-report.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Report: {path}')


if __name__ == '__main__':
    main()
