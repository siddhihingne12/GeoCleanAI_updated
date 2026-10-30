import type { Analysis, DashboardStats, DetectionRecord, GridCell, Health, HotspotData, Panorama, PanoramaAnalysis, Place, ScanJob, ViewSpec } from '../types'
export class ApiError extends Error {
  constructor(message: string, public code: string, public status: number) { super(message) }
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init)
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(body?.error?.message ?? 'The service is unavailable. Please try again.', body?.error?.code ?? 'unavailable', response.status)
  return body as T
}
export const api = {
  health: () => request<Health>('/health'),
  search: (q: string, signal?: AbortSignal) => request<{ places: Place[] }>(`/search?q=${encodeURIComponent(q)}`, { signal }),
  panoramas: (lat: number, lng: number, signal?: AbortSignal) => request<{ panoramas: Panorama[]; truncated: boolean }>(`/panoramas?lat=${lat}&lng=${lng}`, { signal }),
  panorama: (id: string, signal?: AbortSignal) => request<Panorama>(`/panoramas/${id}`, { signal }),
  analyze: (imageId: string, view: ViewSpec, signal?: AbortSignal) => request<Analysis>('/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image_id: imageId, view }), signal }),
  analyzePanorama: async (imageId: string, signal: AbortSignal) => {
    try {
      return await request<PanoramaAnalysis>('/analyze-panorama', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ image_id: imageId }), signal: AbortSignal.any([signal, AbortSignal.timeout(60000)]) })
    } catch (error) {
      if (!signal.aborted && error instanceof DOMException && error.name === 'TimeoutError') throw new ApiError('Litter detection took too long. Please retry.', 'analysis_timeout', 504)
      throw error
    }
  },
  // ── Dashboard APIs ──
  stats: () => request<DashboardStats>('/stats').catch(() => ({ total_detections: 0, total_scans: 0, hotspot_count: 0, high_priority: 0, areas_scanned: 0, areas_total: 0, coverage_pct: 0, severity_distribution: { high: 0, medium: 0, low: 0 }, daily_counts: [] })),
  hotspots: () => request<{ hotspots: HotspotData[] }>('/hotspots').catch(() => ({ hotspots: [] })),
  grids: () => request<{ grids: GridCell[] }>('/grids').catch(() => ({ grids: [] })),
  detections: (limit = 50, severity = '') => request<{ detections: DetectionRecord[] }>(`/detections?limit=${limit}${severity ? `&severity=${severity}` : ''}`).catch(() => ({ detections: [] })),
  scanJobs: () => request<{ jobs: ScanJob[] }>('/scan-jobs').catch(() => ({ jobs: [] })),
  modelComparison: () => request<{ models: { model: string; count: number }[] }>('/model-comparison').catch(() => ({ models: [] })),
}
