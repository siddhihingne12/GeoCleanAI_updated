"""Estimate ground positions of waste detections from street-level image bearings.

Each detection becomes a ray from the camera position along the bearing of the
bounding-box centre. Rays that cross within a small radius are one site; a ray that
meets no other is placed a fixed distance along its bearing and flagged as low
confidence.

All geometry runs in EPSG:32643 (UTM zone 43N) metres. At Pune's latitude a degree of
longitude is about 105 km and a degree of latitude about 111 km, so intersecting rays
in degree space skews every bearing without raising any error. Positions are converted
back to EPSG:4326 only for output.

Input is JSON: a list of observations, or {"observations": [...]}. Each observation
needs image_id, lon, lat, compass_angle, camera_type, class and either bbox_center_x
(normalised 0..1) or bbox (normalised x1, y1, x2, y2). Optional: detection_id,
sequence_id, confidence, captured_at, hfov (degrees, perspective cameras).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from pyproj import Transformer

TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
TO_WGS84 = Transformer.from_crs("EPSG:32643", "EPSG:4326", always_xy=True)

RAY_LENGTH_M = 40.0
CLUSTER_RADIUS_M = 15.0
SINGLE_VIEW_OFFSET_M = 10.0
DEFAULT_PERSPECTIVE_HFOV_DEG = 90.0
# Nearly parallel rays intersect at an unstable, often distant point.
MIN_CROSSING_ANGLE_DEG = 5.0


@dataclass(frozen=True)
class Observation:
    detection_id: str
    image_id: str
    sequence_id: str
    lon: float
    lat: float
    compass_angle: float
    camera_type: str
    bbox_center_x: float
    cls: str
    confidence: float = 1.0
    captured_at: str | None = None
    hfov: float | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Observation":
        if "bbox_center_x" in d:
            cx = float(d["bbox_center_x"])
        elif "bbox" in d:
            cx = (float(d["bbox"][0]) + float(d["bbox"][2])) / 2.0
        else:
            raise ValueError(f"observation {d.get('image_id')} needs bbox_center_x or bbox")
        if not 0.0 <= cx <= 1.0:
            raise ValueError(f"observation {d.get('image_id')}: bbox centre must be normalised to 0..1")
        return cls(
            detection_id=str(d.get("detection_id", d["image_id"])),
            image_id=str(d["image_id"]),
            sequence_id=str(d.get("sequence_id", "")),
            lon=float(d["lon"]),
            lat=float(d["lat"]),
            compass_angle=float(d["compass_angle"]),
            camera_type=str(d["camera_type"]),
            bbox_center_x=cx,
            cls=str(d["class"]),
            confidence=float(d.get("confidence", 1.0)),
            captured_at=d.get("captured_at"),
            hfov=float(d["hfov"]) if d.get("hfov") is not None else None,
        )


@dataclass(frozen=True)
class Ray:
    obs: Observation
    x: float
    y: float
    bearing: float

    @property
    def direction(self) -> tuple[float, float]:
        rad = math.radians(self.bearing)
        return math.sin(rad), math.cos(rad)


def bearing_for(obs: Observation, offset_deg: float = 0.0) -> float:
    """Compass bearing, degrees clockwise from north, of the bbox centre."""
    frac = obs.bbox_center_x - 0.5
    if obs.camera_type in ("spherical", "equirectangular"):
        # Equirectangular panoramas map pixel column linearly onto 360 degrees.
        angular = frac * 360.0
    else:
        # A pinhole image maps pixel offset through tan, not linearly.
        hfov = obs.hfov if obs.hfov is not None else DEFAULT_PERSPECTIVE_HFOV_DEG
        focal = 0.5 / math.tan(math.radians(hfov / 2.0))
        angular = math.degrees(math.atan(frac / focal))
    return (obs.compass_angle + angular + offset_deg) % 360.0


def make_ray(obs: Observation, offset_deg: float = 0.0) -> Ray:
    x, y = TO_UTM.transform(obs.lon, obs.lat)
    return Ray(obs, x, y, bearing_for(obs, offset_deg))


def _cross(ax: float, ay: float, bx: float, by: float) -> float:
    return ax * by - ay * bx


def intersect(a: Ray, b: Ray, ray_length: float = RAY_LENGTH_M) -> tuple[float, float] | None:
    """Crossing point of two capped rays in UTM metres, or None."""
    adx, ady = a.direction
    bdx, bdy = b.direction
    denom = _cross(adx, ady, bdx, bdy)
    if abs(denom) < math.sin(math.radians(MIN_CROSSING_ANGLE_DEG)):
        return None
    wx, wy = b.x - a.x, b.y - a.y
    t = _cross(wx, wy, bdx, bdy) / denom
    s = _cross(wx, wy, adx, ady) / denom
    if not (0.0 < t <= ray_length and 0.0 < s <= ray_length):
        return None
    return a.x + t * adx, a.y + t * ady


def _site(cls: str, rays: list[Ray], x: float, y: float, method: str, spread: float | None) -> dict:
    lon, lat = TO_WGS84.transform(x, y)
    times = sorted(r.obs.captured_at for r in rays if r.obs.captured_at)
    ranges = [math.hypot(x - r.x, y - r.y) for r in rays]
    return {
        "lon": round(lon, 7),
        "lat": round(lat, 7),
        "class": cls,
        "view_count": len(rays),
        "method": method,
        "confidence": round(sum(r.obs.confidence for r in rays) / len(rays), 3),
        "first_seen": times[0] if times else None,
        "last_seen": times[-1] if times else None,
        "intersection_spread_m": None if spread is None else round(spread, 2),
        "mean_range_m": round(sum(ranges) / len(ranges), 2),
        "image_ids": [r.obs.image_id for r in rays],
        "detection_ids": [r.obs.detection_id for r in rays],
        "sequence_ids": sorted({r.obs.sequence_id for r in rays if r.obs.sequence_id}),
        "bearings_deg": [round(r.bearing, 2) for r in rays],
    }


def locate_sites(
    observations: list[Observation],
    cluster_radius: float = CLUSTER_RADIUS_M,
    ray_length: float = RAY_LENGTH_M,
    bearing_offset_deg: float = 0.0,
) -> list[dict]:
    """Group detections into sites. Rays of different classes never combine."""
    by_class: dict[str, list[Observation]] = defaultdict(list)
    for obs in observations:
        by_class[obs.cls].append(obs)

    sites: list[dict] = []
    for cls in sorted(by_class):
        rays = [make_ray(o, bearing_offset_deg) for o in by_class[cls]]
        crossings = []
        for i in range(len(rays)):
            for j in range(i + 1, len(rays)):
                # Two boxes in one image give no independent viewpoint.
                if rays[i].obs.image_id == rays[j].obs.image_id:
                    continue
                point = intersect(rays[i], rays[j], ray_length)
                if point is not None:
                    crossings.append((i, j, point))

        unused = set(range(len(rays)))
        while True:
            live = [c for c in crossings if c[0] in unused and c[1] in unused]
            if not live:
                break

            # Seed each site at the crossing with the most neighbouring crossings, so a
            # stray crossing does not pull a dense cluster apart.
            def support(c):
                return sum(1 for q in live if math.dist(c[2], q[2]) <= cluster_radius)

            seed = max(live, key=support)
            members = [q for q in live if math.dist(seed[2], q[2]) <= cluster_radius]
            ray_ids = sorted({k for q in members for k in q[:2]})
            cx = sum(q[2][0] for q in members) / len(members)
            cy = sum(q[2][1] for q in members) / len(members)
            spread = math.sqrt(sum(math.dist((cx, cy), q[2]) ** 2 for q in members) / len(members))
            sites.append(_site(cls, [rays[k] for k in ray_ids], cx, cy, "intersection", spread))
            unused -= set(ray_ids)

        for k in sorted(unused):
            ray = rays[k]
            dx, dy = ray.direction
            x, y = ray.x + dx * SINGLE_VIEW_OFFSET_M, ray.y + dy * SINGLE_VIEW_OFFSET_M
            sites.append(_site(cls, [ray], x, y, "single_view_offset", None))
    return sites


def to_geojson(sites: list[dict], rays: list[Ray] | None = None, ray_length: float = RAY_LENGTH_M) -> dict:
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {k: v for k, v in s.items() if k not in ("lon", "lat")},
        }
        for s in sites
    ]
    for ray in rays or []:
        dx, dy = ray.direction
        end = TO_WGS84.transform(ray.x + dx * ray_length, ray.y + dy * ray_length)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[ray.obs.lon, ray.obs.lat], [round(end[0], 7), round(end[1], 7)]]},
            "properties": {"kind": "ray", "image_id": ray.obs.image_id, "class": ray.obs.cls, "bearing_deg": round(ray.bearing, 2)},
        })
    return {"type": "FeatureCollection", "features": features}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="observations JSON")
    parser.add_argument("output", type=Path, help="GeoJSON to write")
    parser.add_argument("--bearing-offset", type=float, default=0.0,
                        help="degrees added to every bearing, for heading-sensitivity checks")
    parser.add_argument("--cluster-radius", type=float, default=CLUSTER_RADIUS_M)
    parser.add_argument("--include-rays", action="store_true", help="also write each ray as a LineString")
    args = parser.parse_args(argv)

    raw = json.loads(args.input.read_text(encoding="utf-8"))
    items = raw["observations"] if isinstance(raw, dict) else raw
    observations = [Observation.from_dict(d) for d in items]
    sites = locate_sites(observations, cluster_radius=args.cluster_radius, bearing_offset_deg=args.bearing_offset)
    rays = [make_ray(o, args.bearing_offset) for o in observations] if args.include_rays else None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(to_geojson(sites, rays), indent=2), encoding="utf-8")
    for s in sites:
        spread = "" if s["intersection_spread_m"] is None else f" spread={s['intersection_spread_m']} m"
        print(f"{s['class']}: {s['method']} views={s['view_count']} at {s['lat']}, {s['lon']}"
              f" range={s['mean_range_m']} m{spread}")
    print(f"Wrote {len(sites)} site(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
