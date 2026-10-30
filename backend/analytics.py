"""Analytics and reporting for the GeoClean AI dashboard."""
from backend import database


def get_dashboard_stats() -> dict:
    stats = database.get_stats()
    total = stats['areas_total'] or 1
    stats['coverage_pct'] = round(stats['areas_scanned'] / total * 100, 1)
    return stats


def get_severity_distribution() -> dict:
    return database.get_stats()['severity_distribution']


def get_model_comparison() -> list[dict]:
    from backend.database import _conn
    conn = _conn()
    rows = conn.execute(
        'SELECT model_used, COUNT(*) as count FROM waste_detections GROUP BY model_used ORDER BY count DESC'
    ).fetchall()
    return [{'model': r['model_used'], 'count': r['count']} for r in rows]
