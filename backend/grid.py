"""Pune 500m grid system for systematic area scanning."""

from backend.config import PUNE_BOUNDS

# ~0.0045 degrees ≈ 500m at Pune's latitude (~18.5°N)
CELL_SIZE = 0.0045


def generate_pune_grid() -> list[dict]:
    """Divide PUNE_BOUNDS into ~500m × 500m cells.

    Each cell is a dict with id, lat_min, lat_max, lng_min, lng_max.
    """
    west, south, east, north = PUNE_BOUNDS
    cells: list[dict] = []
    cell_id = 0

    lat = south
    while lat < north:
        lng = west
        while lng < east:
            cells.append({
                'id': f'grid-{cell_id}',
                'lat_min': round(lat, 6),
                'lat_max': round(min(lat + CELL_SIZE, north), 6),
                'lng_min': round(lng, 6),
                'lng_max': round(min(lng + CELL_SIZE, east), 6),
            })
            cell_id += 1
            lng += CELL_SIZE
        lat += CELL_SIZE

    return cells


def find_grid_cell(lat: float, lng: float) -> str | None:
    """Return the grid cell ID containing the given point, or None."""
    west, south, east, north = PUNE_BOUNDS
    if not (south <= lat <= north and west <= lng <= east):
        return None

    col = int((lng - west) / CELL_SIZE)
    row = int((lat - south) / CELL_SIZE)
    cols_per_row = int((east - west) / CELL_SIZE) + 1
    cell_id = row * cols_per_row + col
    return f'grid-{cell_id}'
