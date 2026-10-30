import { useEffect, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import type { Map as LibreMap, Marker } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'
import { AlertCircle, Compass, LocateFixed, MapPin } from 'lucide-react'
import type { Panorama, Place, HotspotData } from '../types'
import { Button } from './ui/button'

export const PUNE_CENTER: [number, number] = [73.8567, 18.5204]
export const PUNE_BOUNDS: [[number, number], [number, number]] = [[73.70, 18.40], [74.05, 18.70]]
maplibregl.setWorkerUrl(workerUrl)
export function inPune(lat: number, lng: number) { return lat >= 18.40 && lat <= 18.70 && lng >= 73.70 && lng <= 74.05 }

interface Props { panoramas: Panorama[]; selected: Panorama | null; focus: Place | null; onPoint: (lat: number, lng: number) => void; onSelect: (p: Panorama) => void; hotspots?: HotspotData[] }
export default function MapPanel(props: Props) {
  const container = useRef<HTMLDivElement>(null), mapRef = useRef<LibreMap | null>(null), markers = useRef<Marker[]>([]), placeMarker = useRef<Marker | null>(null)
  const hotspotMarkers = useRef<Marker[]>([])
  const latest = useRef(props); latest.current = props
  const [error, setError] = useState(false), [ready, setReady] = useState(false)

  useEffect(() => {
    if (!container.current) return
    let map: LibreMap
    try {
      map = new maplibregl.Map({ container: container.current, style: 'https://tiles.openfreemap.org/styles/liberty', center: PUNE_CENTER, zoom: 12.5, maxBounds: PUNE_BOUNDS, minZoom: 10, maxZoom: 19, attributionControl: { compact: true } })
    } catch { setError(true); return }
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'bottom-right')
    map.on('load', () => { setReady(true); setError(false) })
    map.on('error', () => setError(true))
    map.on('click', event => { if (inPune(event.lngLat.lat, event.lngLat.lng)) latest.current.onPoint(event.lngLat.lat, event.lngLat.lng) })
    const observer = new ResizeObserver(() => map.resize())
    observer.observe(container.current)
    return () => { observer.disconnect(); markers.current.forEach(m => m.remove()); placeMarker.current?.remove(); hotspotMarkers.current.forEach(m => m.remove()); map.remove(); mapRef.current = null }
  }, [])

  // Panorama markers
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    markers.current.forEach(m => m.remove())
    markers.current = props.panoramas.map(p => {
      const button = document.createElement('button')
      button.type = 'button'; button.className = `pano-marker ${props.selected?.id === p.id ? 'selected' : ''}`
      button.setAttribute('aria-label', `Open panorama ${p.id}`)
      button.title = `${p.distance_m ?? 0} m from your selection`
      button.addEventListener('click', event => { event.stopPropagation(); latest.current.onSelect(p) })
      return new maplibregl.Marker({ element: button }).setLngLat([p.lng, p.lat]).addTo(map)
    })
  }, [props.panoramas, props.selected?.id, ready])

  // Place marker
  useEffect(() => {
    const location = props.focus
    const map = mapRef.current
    placeMarker.current?.remove(); placeMarker.current = null
    if (!location || !map || !inPune(location.lat, location.lng)) return
    const pin = document.createElement('div')
    pin.className = 'place-marker'; pin.setAttribute('role', 'img'); pin.setAttribute('aria-label', `Selected place: ${location.name}`)
    pin.title = location.name
    pin.appendChild(document.createElement('span'))
    pin.addEventListener('click', event => event.stopPropagation())
    placeMarker.current = new maplibregl.Marker({ element: pin, anchor: 'bottom' }).setLngLat([location.lng, location.lat]).addTo(map)
    map.flyTo({ center: [location.lng, location.lat], zoom: 16, duration: 900 })
    return () => { placeMarker.current?.remove(); placeMarker.current = null }
  }, [props.focus, ready])

  // Selected panorama fly-to
  useEffect(() => {
    const location = props.selected
    if (location && mapRef.current && inPune(location.lat, location.lng)) mapRef.current.flyTo({ center: [location.lng, location.lat], zoom: 16, duration: 900 })
  }, [props.selected?.id, ready])

  // Heatmap layer for hotspots
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const hotspots = props.hotspots ?? []

    // Remove old hotspot markers
    hotspotMarkers.current.forEach(m => m.remove())
    hotspotMarkers.current = []

    // Add hotspot markers with pulsing dots
    hotspots.forEach(h => {
      const el = document.createElement('div')
      el.className = `hotspot-map-dot priority-${h.priority}`
      el.title = `${h.priority.toUpperCase()} priority hotspot: ${h.detection_count} detections`
      el.style.cssText = `width:${h.priority === 'high' ? 18 : h.priority === 'medium' ? 14 : 10}px;height:${h.priority === 'high' ? 18 : h.priority === 'medium' ? 14 : 10}px;border-radius:50%;background:${h.priority === 'high' ? '#ef4444' : h.priority === 'medium' ? '#f59e0b' : '#10b981'};border:2px solid ${h.priority === 'high' ? '#fca5a5' : h.priority === 'medium' ? '#fcd34d' : '#6ee7b7'};box-shadow:0 0 ${h.priority === 'high' ? '12' : '6'}px ${h.priority === 'high' ? '#ef444480' : h.priority === 'medium' ? '#f59e0b60' : '#10b98140'};cursor:pointer;`
      if (h.priority === 'high') el.style.animation = 'pulse-glow-red 2s infinite'
      el.addEventListener('click', (e) => { e.stopPropagation(); latest.current.onPoint(h.lat, h.lng) })
      const marker = new maplibregl.Marker({ element: el }).setLngLat([h.lng, h.lat]).addTo(map)
      hotspotMarkers.current.push(marker)
    })

    // Add/update heatmap source & layer
    try {
      const geojson = {
        type: 'FeatureCollection',
        features: hotspots.map(h => ({
          type: 'Feature' as const,
          geometry: { type: 'Point' as const, coordinates: [h.lng, h.lat] },
          properties: { score: h.score, priority: h.priority, count: h.detection_count },
        })),
      }

      if (map.getSource('hotspots-heat')) {
        (map.getSource('hotspots-heat') as maplibregl.GeoJSONSource).setData(geojson)
      } else if (hotspots.length > 0) {
        map.addSource('hotspots-heat', { type: 'geojson', data: geojson })
        map.addLayer({
          id: 'hotspot-heat-layer',
          type: 'heatmap',
          source: 'hotspots-heat',
          paint: {
            'heatmap-weight': ['get', 'score'],
            'heatmap-intensity': 1.5,
            'heatmap-color': [
              'interpolate', ['linear'], ['heatmap-density'],
              0, 'rgba(0,0,0,0)',
              0.2, '#10b981',
              0.4, '#34d399',
              0.6, '#f59e0b',
              0.8, '#ef4444',
              1, '#dc2626',
            ],
            'heatmap-radius': 35,
            'heatmap-opacity': 0.6,
          },
        })
      }
    } catch {
      // Heatmap layer is non-critical
    }

    return () => { hotspotMarkers.current.forEach(m => m.remove()); hotspotMarkers.current = [] }
  }, [props.hotspots, ready])

  return <section className="panel map-panel" aria-label="Pune location map">
    <div className="panel-heading"><span className="eyebrow"><span className="step-number">01</span> FIND A STREET</span><span className="subtle-label"><MapPin size={13} /> Pune only</span></div>
    <div className="map-stage">
      <div ref={container} className="map-container" data-testid="map-container" />
      {!ready && !error && <div className="map-loading"><Compass className="animate-spin" size={20} /><span>Opening Pune map…</span></div>}
      {error && <div className="map-notice"><AlertCircle size={16} /> Map tiles are unavailable. You can still use search or the area shortcuts.</div>}
      <div className="map-top-note"><span className="live-dot" />{props.focus ? 'Your place is pinned. Open a nearby street view.' : 'Search a place or choose a point on the map'}</div>
      <Button variant="outline" size="icon" className="recenter" title="Recenter on Pune" aria-label="Recenter on Pune" onClick={() => mapRef.current?.flyTo({ center: PUNE_CENTER, zoom: 12.5 })}><LocateFixed /></Button>
      <div className="map-key"><span className="key-dot place"/> Your place <span className="key-dot" /> Street photo <span className="key-dot outlined" /> Open photo</div>
    </div>
    <div className="panel-foot"><span>Camera locations · Hotspots shown as colored dots</span><span>18.5204° N, 73.8567° E</span></div>
  </section>
}
