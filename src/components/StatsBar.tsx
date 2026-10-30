import { Camera, AlertTriangle, Flame, MapPin } from 'lucide-react'
import type { DashboardStats } from '../types'

interface Props { stats: DashboardStats }

export function StatsBar({ stats }: Props) {
  const cards = [
    { label: 'Panoramas Scanned', value: stats.total_scans, icon: <Camera size={20} />, color: '#3b82f6', accent: 'stat-blue' },
    { label: 'Waste Detected', value: stats.total_detections, icon: <AlertTriangle size={20} />, color: '#f59e0b', accent: 'stat-amber' },
    { label: 'Active Hotspots', value: stats.hotspot_count, icon: <Flame size={20} />, color: '#ef4444', accent: 'stat-red', badge: stats.high_priority > 0 ? `${stats.high_priority} HIGH` : undefined },
    { label: 'Area Coverage', value: `${stats.coverage_pct}%`, icon: <MapPin size={20} />, color: '#10b981', accent: 'stat-green', sub: `${stats.areas_scanned} / ${stats.areas_total} grids` },
  ]
  return (
    <div className="stats-bar">
      {cards.map(card => (
        <div key={card.label} className={`stat-card ${card.accent}`}>
          <div className="stat-accent" style={{ background: card.color }} />
          <div className="stat-body">
            <div className="stat-icon" style={{ color: card.color }}>{card.icon}</div>
            <div>
              <div className="stat-value">{typeof card.value === 'number' ? card.value.toLocaleString() : card.value}</div>
              <div className="stat-label">{card.label}</div>
              {card.badge && <span className="stat-badge-alert">{card.badge}</span>}
              {card.sub && <span className="stat-sub">{card.sub}</span>}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

