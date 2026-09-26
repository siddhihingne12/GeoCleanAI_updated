"""Read real Mapillary coverage and write a candidate report, never fake sample pins."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.providers import nearby, get_image, download_panorama

AREAS = [('Shivajinagar',18.5314,73.8446),('Koregaon Park',18.5362,73.8939),('Kothrud',18.5074,73.8077),('Central Pune',18.5204,73.8567),('Hadapsar',18.5089,73.9260)]

def check(output: Path):
    report = []
    for name, lat, lng in AREAS:
        result = nearby(lat,lng)
        report.append({'area': name, **result})
        print(f'{name}: {len(result["panoramas"])} panoramas within 500 m; subset={result["truncated"]}')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2))
    print('Candidates only. Visually verify image quality and litter before adding IDs to public/samples.json.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('artifacts/coverage.json'))
    parser.add_argument('--image',help='Download one candidate for local visual inspection')
    args = parser.parse_args()
    if args.image:
        item, meta = get_image(args.image, original=True)
        image = download_panorama(item)
        path = Path('artifacts')/f'panorama-{args.image}.jpg'; path.parent.mkdir(exist_ok=True)
        image.save(path)
        print(json.dumps({**meta, 'local_path':str(path), 'width':image.width, 'height':image.height},indent=2))
    else:
        check(args.output)
