import { Flame, MapPin, ArrowUpRight } from 'lucide-react'
import { SeverityBadge } from './SeverityBadge'
import type { HotspotData } from '../types'

interface Props {
  hotspots: HotspotData[]
  onSelect: (h: HotspotData) => void
}

export function HotspotPanel({ hotspots, onSelect }: Props) {
  if (!hotspots.length) {
    return (
      <section className="hotspot-panel">
        <div className="hotspot-heading"><Flame size={16} /><span>Dumping Hotspots</span><span className="hotspot-count">0 found</span></div>
        <div className="hotspot-empty"><MapPin size={18} /><span>No hotspots detected yet. Scan panoramas to identify waste accumulation zones.</span></div>
      </section>
    )
  }
  return (
    <section className="hotspot-panel">
      <div className="hotspot-heading"><Flame size={16} /><span>Dumping Hotspots</span><span className="hotspot-count">{hotspots.length} found</span></div>
      <div className="hotspot-list">
        {hotspots.slice(0, 10).map(h => (
          <button key={h.id} className="hotspot-item" onClick={() => onSelect(h)}>
            <div className={`hotspot-dot priority-${h.priority}`} />
            <div className="hotspot-info">
              <strong>{h.detection_count} detections</strong>
              <span>{h.lat.toFixed(4)}° N, {h.lng.toFixed(4)}° E</span>
            </div>
            <SeverityBadge level={h.priority} />
            <span className="hotspot-score">{Math.round(h.score * 100)}%</span>
            <ArrowUpRight size={14} />
          </button>
        ))}
      </div>
    </section>
  )
}

