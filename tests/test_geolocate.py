import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import geolocate as g  # noqa: E402

# A reference point in Aundh, Pune, expressed in UTM 43N metres.
TARGET = g.TO_UTM.transform(73.8116, 18.5675)


def camera_seeing(cam_x, cam_y, target, image_id, cls="roadside_dump", sequence="s1"):
    """A spherical-camera observation whose box centre points exactly at target."""
    bearing = math.degrees(math.atan2(target[0] - cam_x, target[1] - cam_y))
    lon, lat = g.TO_WGS84.transform(cam_x, cam_y)
    return g.Observation(
        detection_id=image_id, image_id=image_id, sequence_id=sequence, lon=lon, lat=lat,
        compass_angle=0.0, camera_type="spherical", bbox_center_x=0.5 + bearing / 360.0, cls=cls,
    )


def metres_between(site, point):
    return math.dist(g.TO_UTM.transform(site["lon"], site["lat"]), point)


class GeolocateTest(unittest.TestCase):
    def test_two_cameras_20m_apart_intersect_at_known_point(self):
        tx, ty = TARGET
        obs = [camera_seeing(tx - 10, ty - 15, TARGET, "a"), camera_seeing(tx + 10, ty - 15, TARGET, "b")]
        sites = g.locate_sites(obs)
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]["method"], "intersection")
        self.assertEqual(sites[0]["view_count"], 2)
        self.assertLess(metres_between(sites[0], TARGET), 1.0)

    def test_spherical_pixel_column_maps_linearly_to_bearing(self):
        obs = camera_seeing(*TARGET, TARGET, "a")
        self.assertAlmostEqual(g.bearing_for(obs.__class__(**{**obs.__dict__, "compass_angle": 180.0, "bbox_center_x": 0.25})), 90.0)

    def test_perspective_offset_uses_pinhole_projection(self):
        base = dict(detection_id="p", image_id="p", sequence_id="", lon=73.81, lat=18.56,
                    compass_angle=0.0, camera_type="perspective", cls="roadside_dump")
        edge = g.Observation(**base, bbox_center_x=1.0)
        quarter = g.Observation(**base, bbox_center_x=0.75)
        self.assertAlmostEqual(g.bearing_for(edge), 45.0)
        self.assertAlmostEqual(g.bearing_for(quarter), math.degrees(math.atan(0.5)))

    def test_single_view_is_placed_10m_along_bearing(self):
        tx, ty = TARGET
        sites = g.locate_sites([camera_seeing(tx, ty - 30, TARGET, "only")])
        self.assertEqual(sites[0]["method"], "single_view_offset")
        self.assertLess(metres_between(sites[0], (tx, ty - 20)), 0.01)

    def test_rays_pointing_away_from_each_other_do_not_combine(self):
        tx, ty = TARGET
        obs = [camera_seeing(tx - 10, ty, (tx - 40, ty), "west"), camera_seeing(tx + 10, ty, (tx + 40, ty), "east")]
        sites = g.locate_sites(obs)
        self.assertEqual([s["method"] for s in sites], ["single_view_offset", "single_view_offset"])

    def test_separate_dumps_stay_separate(self):
        tx, ty = TARGET
        far = (tx + 60, ty)
        obs = [
            camera_seeing(tx - 10, ty - 15, TARGET, "a1"), camera_seeing(tx + 10, ty - 15, TARGET, "a2"),
            camera_seeing(far[0] - 10, ty - 15, far, "b1"), camera_seeing(far[0] + 10, ty - 15, far, "b2"),
        ]
        sites = g.locate_sites(obs)
        self.assertEqual(len(sites), 2)
        for site, expected in zip(sorted(sites, key=lambda s: s["lon"]), (TARGET, far)):
            self.assertEqual(site["method"], "intersection")
            self.assertLess(metres_between(site, expected), 1.0)

    def test_different_classes_never_combine(self):
        tx, ty = TARGET
        obs = [camera_seeing(tx - 10, ty - 15, TARGET, "a"),
               camera_seeing(tx + 10, ty - 15, TARGET, "b", cls="overflowing_bin")]
        self.assertEqual(len(g.locate_sites(obs)), 2)

    def test_intersection_in_degrees_would_be_wrong(self):
        # Guards the reason for projecting: the same bearings intersected in raw
        # lon/lat degrees land metres away from the true point.
        tx, ty = TARGET
        a = camera_seeing(tx - 10, ty - 15, TARGET, "a")
        b = camera_seeing(tx + 10, ty - 15, TARGET, "b")
        ra, rb = (g.Ray(o, o.lon, o.lat, g.bearing_for(o)) for o in (a, b))
        lon_lat = g.intersect(ra, rb, ray_length=1.0)
        self.assertIsNotNone(lon_lat)
        self.assertGreater(math.dist(g.TO_UTM.transform(*lon_lat), TARGET), 0.5)


if __name__ == "__main__":
    unittest.main()
