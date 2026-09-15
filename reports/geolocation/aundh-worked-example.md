# Geolocation worked example: Aundh bridge-railing dump

Run 13 September 2026 with `scripts/geolocate.py`. It demonstrates the ray-intersection method on the only confirmed Pune positive, not an accuracy evaluation. The 80%-within-15-m target needs many checkable sites.

## Inputs

- **Imagery:** Mapillary sequence `BEohfHsAZiWFlVXwp7Gz4N`, a roof-mounted 360-degree camera heading south, captured 17 September 2025. Four frames about 6 m apart: F3, F5, F7, F9.
- **Positions and headings:** from the Mapillary API ([mapillary-geometry.json](../visual-review/pune-aundh-adjacent-bridge/mapillary-geometry.json)); compass 178-180 degrees.
- **Detections:** there is no trained detector yet, so the pile's horizontal centre was read by eye from gridded strips of the 2048 x 1024 panoramas: F3 = 775 px, F5 = 705, F7 = 530, F9 = 250. Reading accuracy is about +/-20 px, or +/-3.5 degrees. Inputs: [config/aundh-dump-observations.json](../../config/aundh-dump-observations.json).
- **Bearing model:** equirectangular column maps linearly to bearing, with the image centre at the Mapillary compass angle. All ray math runs in EPSG:32643 metres.

## Result

| Heading assumption | Site (lat, lon) | Views | Mean range | Crossing spread |
|---|---|---:|---:|---:|
| Mapillary compass as recorded | 18.5675349, 73.8116811 | 4 | 12.8 m | 5.1 m |
| Compass shifted -13 degrees | 18.5675594, 73.8116904 | 4 | 13.3 m | 7.7 m |

GeoJSON with the site and all four rays: [aundh-dump-sites.geojson](aundh-dump-sites.geojson), [aundh-dump-sites-offset-13.geojson](aundh-dump-sites-offset-13.geojson).

- All four rays combine into one `intersection` site, placed about 10.5 m east of the camera track, level with frame F7. That matches F7's near-perpendicular view of the pile on the left-hand railing.
- **Heading sensitivity is small.** The far road converges near column 950 rather than the image centre (1024), so the true heading may differ from the recorded compass by up to about 13 degrees. Applying that shift moves the site only 2.9 m.
- **The crossing spread of 5-8 m is mostly the pile's own length.** It stretches several railing bays, and each frame's centre reading lands on a different part of it.

## Limitations

- The estimate has not been compared with an independent reference position, such as the railing line in OpenStreetMap or a Mapillary map view. That remote check is still to do.
- Hand-read centres stand in for detector boxes. Real detections will add their own box-centre noise.
- One site cannot support an accuracy statistic.

## Unit tests

`.venv\Scripts\python.exe -m unittest tests.test_geolocate -v`: 8 tests pass. They cover the blueprint's two synthetic cameras 20 m apart (intersection within 1 m of the true point), spherical and pinhole bearing mapping, single-view fallback, non-crossing rays, separate sites, class separation, and a check that intersecting in raw degrees misplaces the point.
