"""SQLite database for GeoClean AI detection persistence and hotspot tracking."""
import json
import sqlite3
import threading
import time
from backend.config import ROOT, PUNE_BOUNDS

DB_PATH = ROOT / 'data' / 'geoclean.db'
_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, 'conn') or _local.conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute('PRAGMA journal_mode=WAL')
        _local.conn.execute('PRAGMA foreign_keys=ON')
    return _local.conn


def init_db():
    conn = _conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS waste_detections (
            id TEXT PRIMARY KEY, image_id TEXT NOT NULL, lat REAL NOT NULL, lng REAL NOT NULL,
            label TEXT NOT NULL DEFAULT 'waste', confidence REAL NOT NULL,
            waste_area_pct REAL, severity TEXT NOT NULL DEFAULT 'medium',
            box_json TEXT, model_used TEXT DEFAULT 'unknown',
            detected_at INTEGER NOT NULL, view_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_det_image ON waste_detections(image_id);
        CREATE INDEX IF NOT EXISTS idx_det_severity ON waste_detections(severity);
        CREATE INDEX IF NOT EXISTS idx_det_date ON waste_detections(detected_at);
        CREATE TABLE IF NOT EXISTS hotspots (
            id TEXT PRIMARY KEY, lat REAL NOT NULL, lng REAL NOT NULL,
            radius_m REAL DEFAULT 100, priority TEXT NOT NULL DEFAULT 'low',
            score REAL DEFAULT 0, detection_count INTEGER DEFAULT 0,
            last_seen INTEGER, first_seen INTEGER,
            avg_confidence REAL DEFAULT 0, description TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS hotspot_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, hotspot_id TEXT NOT NULL,
            detection_id TEXT NOT NULL, observed_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pune_grids (
            id TEXT PRIMARY KEY, lat_min REAL NOT NULL, lat_max REAL NOT NULL,
            lng_min REAL NOT NULL, lng_max REAL NOT NULL,
            detection_count INTEGER DEFAULT 0, scanned INTEGER DEFAULT 0, last_scanned INTEGER
        );
        CREATE TABLE IF NOT EXISTS scan_jobs (
            id TEXT PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending',
            area_name TEXT DEFAULT '', total_images INTEGER DEFAULT 0,
            processed INTEGER DEFAULT 0, detections_found INTEGER DEFAULT 0,
            started_at INTEGER NOT NULL, completed_at INTEGER
        );
    ''')
    conn.commit()
    _populate_grids(conn)


def _populate_grids(conn):
    if conn.execute('SELECT COUNT(*) FROM pune_grids').fetchone()[0] > 0:
        return
    west, south, east, north = PUNE_BOUNDS
    step = 0.0045
    rows, gid = [], 0
    lat = south
    while lat < north:
        lng = west
        while lng < east:
            gid += 1
            rows.append((f'grid-{gid}', round(lat, 6), round(min(lat + step, north), 6),
                         round(lng, 6), round(min(lng + step, east), 6), 0, 0, None))
            lng += step
        lat += step
    conn.executemany('INSERT INTO pune_grids VALUES (?,?,?,?,?,?,?,?)', rows)
    conn.commit()


def save_detection(det_id, image_id, lat, lng, label, confidence, box,
                   severity='medium', waste_area_pct=None, model_used='unknown', view_id=None):
    conn = _conn()
    conn.execute(
        'INSERT OR REPLACE INTO waste_detections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        (det_id, image_id, lat, lng, label, confidence, waste_area_pct, severity,
         json.dumps(box), model_used, int(time.time()), view_id))
    conn.commit()
    _update_grid(conn, lat, lng)


def get_detections(limit=50, offset=0, severity_filter=None):
    conn = _conn()
    if severity_filter in ('high', 'medium', 'low'):
        rows = conn.execute('SELECT * FROM waste_detections WHERE severity=? ORDER BY detected_at DESC LIMIT ? OFFSET ?',
                            (severity_filter, limit, offset)).fetchall()
    else:
        rows = conn.execute('SELECT * FROM waste_detections ORDER BY detected_at DESC LIMIT ? OFFSET ?',
                            (limit, offset)).fetchall()
    return [dict(r) for r in rows]


def save_hotspot(hs_id, lat, lng, priority, score, detection_count, avg_confidence, description='', radius_m=100):
    conn = _conn()
    now = int(time.time())
    ex = conn.execute('SELECT first_seen FROM hotspots WHERE id=?', (hs_id,)).fetchone()
    first = ex['first_seen'] if ex else now
    conn.execute('INSERT OR REPLACE INTO hotspots VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                 (hs_id, lat, lng, radius_m, priority, round(score, 4), detection_count,
                  now, first, round(avg_confidence, 4), description))
    conn.commit()


def get_hotspots():
    return [dict(r) for r in _conn().execute('SELECT * FROM hotspots ORDER BY score DESC').fetchall()]


def get_hotspot(hs_id):
    r = _conn().execute('SELECT * FROM hotspots WHERE id=?', (hs_id,)).fetchone()
    return dict(r) if r else None


def get_grids():
    return [dict(r) for r in _conn().execute('SELECT * FROM pune_grids ORDER BY id').fetchall()]


def mark_grid_scanned(grid_id):
    conn = _conn()
    conn.execute('UPDATE pune_grids SET scanned=1, last_scanned=? WHERE id=?', (int(time.time()), grid_id))
    conn.commit()


def _update_grid(conn, lat, lng):
    r = conn.execute('SELECT id FROM pune_grids WHERE lat_min<=? AND lat_max>=? AND lng_min<=? AND lng_max>=? LIMIT 1',
                     (lat, lat, lng, lng)).fetchone()
    if r:
        conn.execute('UPDATE pune_grids SET detection_count=detection_count+1, scanned=1, last_scanned=? WHERE id=?',
                     (int(time.time()), r['id']))


def save_scan_job(job_id, area_name='', total_images=0):
    conn = _conn()
    now = int(time.time())
    conn.execute('INSERT INTO scan_jobs VALUES (?,?,?,?,?,?,?,?)',
                 (job_id, 'running', area_name, total_images, 0, 0, now, None))
    conn.commit()


def update_scan_job(job_id, **kwargs):
    conn = _conn()
    sets = ', '.join(f'{k}=?' for k in kwargs)
    conn.execute(f'UPDATE scan_jobs SET {sets} WHERE id=?', (*kwargs.values(), job_id))
    conn.commit()


def get_scan_jobs():
    return [dict(r) for r in _conn().execute('SELECT * FROM scan_jobs ORDER BY started_at DESC LIMIT 50').fetchall()]


def get_stats():
    conn = _conn()
    total_det = conn.execute('SELECT COUNT(*) FROM waste_detections').fetchone()[0]
    total_scans = conn.execute('SELECT COUNT(DISTINCT image_id) FROM waste_detections').fetchone()[0]
    hs_count = conn.execute('SELECT COUNT(*) FROM hotspots').fetchone()[0]
    high_p = conn.execute("SELECT COUNT(*) FROM hotspots WHERE priority='high'").fetchone()[0]
    scanned = conn.execute('SELECT COUNT(*) FROM pune_grids WHERE scanned=1').fetchone()[0]
    total_grids = conn.execute('SELECT COUNT(*) FROM pune_grids').fetchone()[0]
    sev = {level: conn.execute('SELECT COUNT(*) FROM waste_detections WHERE severity=?', (level,)).fetchone()[0]
           for level in ('high', 'medium', 'low')}
    thirty_ago = int(time.time()) - 30 * 86400
    daily = conn.execute(
        "SELECT date(detected_at, 'unixepoch') as day, COUNT(*) as cnt FROM waste_detections WHERE detected_at>=? GROUP BY day ORDER BY day",
        (thirty_ago,)).fetchall()
    return {
        'total_detections': total_det, 'total_scans': total_scans,
        'hotspot_count': hs_count, 'high_priority': high_p,
        'areas_scanned': scanned, 'areas_total': total_grids,
        'severity_distribution': sev,
        'daily_counts': [{'date': r['day'], 'count': r['cnt']} for r in daily],
    }


try:
    init_db()
except Exception:
    pass
