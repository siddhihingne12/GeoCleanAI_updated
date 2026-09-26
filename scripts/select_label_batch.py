"""Choose a spread-out batch of safe Pune panoramas for human labelling (no downloads).

- Candidates come from scripts/find_training_panoramas.py (test sequences and anything within
  300 m of a reviewed panorama are already excluded).
- Within a sequence, chosen panoramas are at least --spacing-m apart (consecutive frames are
  near-duplicates).
- Sequences are visited round-robin so the batch covers as many streets and capture dates as
  possible; the choice within a sequence is seeded.
- Location groups join sequences that pass within --spacing-m of each other. The later
  train/validation split is by group, so the same street can never be on both sides.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.providers import distance_m


def spaced(images: list[dict], spacing: float, rng: random.Random) -> list[dict]:
    order = images[:]
    rng.shuffle(order)
    chosen = []
    for image in order:
        if all(distance_m(image['lat'], image['lng'], c['lat'], c['lng']) >= spacing for c in chosen):
            chosen.append(image)
    return chosen


def location_groups(candidates: list[dict], spacing: float) -> dict[str, str]:
    """Union sequences that come within `spacing` metres of each other."""
    parent = {}
    def root(key):
        parent.setdefault(key, key)
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key
    by_sequence = defaultdict(list)
    for image in candidates:
        by_sequence[image['sequence']].append(image)
        root(image['sequence'])
    sequences = sorted(by_sequence)
    for i, a in enumerate(sequences):
        for b in sequences[i+1:]:
            if root(a) != root(b) and any(distance_m(x['lat'], x['lng'], y['lat'], y['lng']) < spacing
                                          for x in by_sequence[a][::3] for y in by_sequence[b][::3]):
                parent[root(a)] = root(b)
    return {s: root(s) for s in sequences}


def select(report: dict, count: int, spacing: float, seed: int) -> dict:
    rng = random.Random(seed)
    candidates = [c for c in report['candidates'] if c.get('sequence')]
    groups = location_groups(candidates, spacing)
    by_sequence = defaultdict(list)
    for image in candidates:
        by_sequence[image['sequence']].append(image)
    pools = {s: spaced(sorted(v, key=lambda i: i['id']), spacing, rng) for s, v in sorted(by_sequence.items())}
    chosen = []
    while len(chosen) < count and any(pools.values()):
        for sequence in sorted(pools):
            if pools[sequence] and len(chosen) < count:
                chosen.append(pools[sequence].pop(0))
    rows = [{'id': c['id'], 'lat': c['lat'], 'lng': c['lng'], 'captured_at': c['captured_at'], 'creator': c['creator'],
             'sequence': c['sequence'], 'location_group': groups[c['sequence']],
             'path': f"artifacts/panorama-{c['id']}.jpg", 'source_url': f"https://www.mapillary.com/app/?pKey={c['id']}"}
            for c in chosen]
    return {'seed': seed, 'spacing_m': spacing, 'requested': count, 'selected': len(rows),
            'sequences': len({r['sequence'] for r in rows}), 'location_groups': len({r['location_group'] for r in rows}),
            'creators': sorted({r['creator'] for r in rows}), 'candidates': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--report', type=Path, default=Path('artifacts/pune-training-candidates.json'))
    parser.add_argument('--count', type=int, default=40)
    parser.add_argument('--spacing-m', type=float, default=100)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=Path, default=Path('artifacts/pune-label-v1/candidates.json'))
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'{args.output} exists; a labelling batch is never reselected. Choose a new output.')
    batch = select(json.loads(args.report.read_text()), args.count, args.spacing_m, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # export_pune_views expects a plain list of candidates.
    args.output.write_text(json.dumps(batch['candidates'], indent=2))
    args.output.with_name('selection.json').write_text(json.dumps({k: v for k, v in batch.items() if k != 'candidates'}, indent=2))
    print(json.dumps({k: v for k, v in batch.items() if k != 'candidates'}, indent=2))
