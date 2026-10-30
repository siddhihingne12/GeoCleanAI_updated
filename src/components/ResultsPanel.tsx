import { ArrowUpRight, Check, CircleHelp, LoaderCircle, Sparkles } from 'lucide-react'
import { Button } from './ui/button'
import { SeverityBadge } from './SeverityBadge'
import type { Panorama, PanoramaAnalysis, PanoramaDetection } from '../types'

interface Props {
  selected: Panorama | null
  analysis: PanoramaAnalysis | null
  scanning: boolean
  error: string
  unavailable: string
  activeDetection: PanoramaDetection | null
  onDetection: (d: PanoramaDetection) => void
  onRetry: () => void
}

function getSeverity(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.7) return 'high'
  if (confidence >= 0.5) return 'medium'
  return 'low'
}

export function ResultsPanel({ selected, analysis, scanning, error, unavailable, activeDetection, onDetection, onRetry }: Props) {
  const previewId = activeDetection?.view_id ?? analysis?.detections[0]?.view_id ?? analysis?.views[0]?.id
  const preview = analysis?.views.find(view => view.id === previewId)
  const visibleDetections = analysis?.detections.filter(d => d.view_id === previewId) ?? []
  const status = scanning ? 'DETECTING WASTE' : error ? 'DETECTION FAILED' : analysis ? 'ANALYSIS COMPLETE' : unavailable ? 'UNAVAILABLE' : selected ? 'WAITING' : 'OPEN A STREET VIEW'

  return <section className="results-panel" aria-label="AI results" aria-live="polite">
    <div className="results-heading"><div><span className="step-number">03</span><h2>Waste detections</h2></div><span className={`result-status ${analysis ? 'complete' : ''}`}>{status}</span></div>
    {error ? <div className="scan-error"><CircleHelp size={18}/><p>{error}</p><Button size="sm" variant="outline" onClick={onRetry} disabled={Boolean(unavailable)}>Retry detection</Button></div>
      : scanning ? <div className="result-empty"><div className="scan-orb"><LoaderCircle className="animate-spin" size={23}/></div><div><strong>Detecting waste accumulation…</strong><p>AI is scanning all directions for garbage piles, waste heaps and roadside dumping.</p></div></div>
      : analysis ? <div className="analysis-content">
        <div className="analysis-summary"><strong>{analysis.detections.length}</strong><div><span>{analysis.detections.length === 1 ? 'suspected waste area' : 'suspected waste areas'}</span><small>{analysis.cached ? 'Saved result' : 'New analysis'} · {(analysis.elapsed_ms / 1000).toFixed(1)}s · All six directions checked</small></div><Check size={20}/></div>
        {!analysis.detections.length && <p className="small-note">No waste accumulation detected in this panorama. Small or hidden dumping may still be present; this does not confirm the area is clean.</p>}
        <div className="detection-list">{analysis.detections.map((d, i) => <button key={d.id} aria-pressed={activeDetection?.id === d.id} aria-label={`Show waste detection ${i + 1}`} className={activeDetection?.id === d.id ? 'detection active' : 'detection'} onClick={() => onDetection(d)}><span>{String(i + 1).padStart(2, '0')}</span><div className="detection-label-row"><strong>Waste detected</strong><SeverityBadge level={getSeverity(d.confidence)} /></div><small>{Math.round(d.confidence * 100)}% confidence</small><ArrowUpRight size={14}/></button>)}</div>
        {preview && <><div className="scan-preview" data-view-id={preview.id}>
          <img src={preview.preview} alt="Analysed photograph supporting the waste detections"/>
          {visibleDetections.map(d => <span key={d.id} data-detection-id={d.id} className={`detection-box ${activeDetection?.id === d.id ? 'selected' : ''}`} style={{ left: `${d.box[0] * 100}%`, top: `${d.box[1] * 100}%`, width: `${(d.box[2] - d.box[0]) * 100}%`, height: `${(d.box[3] - d.box[1]) * 100}%` }}/>)}</div>
          <p className="small-note">One of six analysed directions. Select a detection to look toward it and see its evidence.</p></>}
        <p className="small-note">AI detections need human review. Confidence is not a measured accuracy score. Photos show conditions on their capture date.</p>
      </div>
      : <div className="result-empty"><div className="result-icon"><Sparkles size={21}/></div><div><strong>{unavailable ? 'Waste detection unavailable' : 'Waste is detected automatically.'}</strong><p>{unavailable || 'Choose a place and open a street view. Suspected waste accumulation will appear here and in the panorama.'}</p></div></div>}
  </section>
}
