export type Point = [number, number]
export type Vec3 = [number, number, number]
export interface Place { id: string; name: string; lat: number; lng: number }
export interface Panorama { id: string; lat: number; lng: number; captured_at: number; creator: string; distance_m?: number; is_pano: boolean; thumbnail_url?: string }
export interface ViewSpec { origin: Vec3; right: Vec3; down: Vec3; aspect: number }
export interface Detection { id: string; label: string; confidence: number; box: [number, number, number, number]; tag: Point }
export interface Analysis { image_id: string; model_version: string; detections: Detection[]; elapsed_ms: number; cached: boolean; view: ViewSpec; preview: string; captured_at: number }
export interface PanoramaDetection extends Detection { view_id: string }
export interface AnalysedView { id: string; view: ViewSpec; preview: string }
export interface PanoramaAnalysis { image_id: string; model_version: string; analysis_version: string; detections: PanoramaDetection[]; views: AnalysedView[]; elapsed_ms: number; cached: boolean; captured_at: number }
export interface Health { status: 'ready' | 'setup_required'; checks: Record<string, boolean>; model_version: string | null; samples: Panorama[] }

// ── Dashboard types ──
export interface HotspotData {
  id: string; lat: number; lng: number; priority: 'high' | 'medium' | 'low'
  score: number; detection_count: number; last_seen: number; first_seen: number
  avg_confidence: number; description: string; radius_m: number
}

export interface GridCell {
  id: string; lat_min: number; lat_max: number; lng_min: number; lng_max: number
  detection_count: number; scanned: number; last_scanned: number | null
}

export interface DashboardStats {
  total_detections: number; total_scans: number; hotspot_count: number
  high_priority: number; areas_scanned: number; areas_total: number
  coverage_pct: number
  severity_distribution: { high: number; medium: number; low: number }
  daily_counts: { date: string; count: number }[]
}

export interface DetectionRecord {
  id: string; image_id: string; lat: number; lng: number; label: string
  confidence: number; waste_area_pct: number | null; severity: 'high' | 'medium' | 'low'
  detected_at: number; model_used: string
}

export interface ScanJob {
  id: string; status: 'pending' | 'running' | 'completed' | 'failed'
  area_name: string; total_images: number; processed: number
  detections_found: number; started_at: number; completed_at: number | null
}
