import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { ArrowRight, ArrowUpRight, CircleHelp, Clock3, Crosshair, ExternalLink, Leaf, LoaderCircle, MapPin, Search, ShieldCheck, SlidersHorizontal, Sparkles, X } from 'lucide-react'
import { Button } from './components/ui/button'
import { InfoDialog } from './components/InfoDialog'
import { ResultsPanel } from './components/ResultsPanel'
import { api } from './lib/api'
import type { PanoramaAnalysis, PanoramaDetection, Health, Panorama, Place } from './types'

const MapPanel = lazy(() => import('./components/MapPanel'))
const StreetViewer = lazy(() => import('./components/StreetViewer').then(m => ({ default: m.StreetViewer })))
const areas: Place[] = [
  { id: 'central', name: 'Central Pune', lat: 18.5204, lng: 73.8567 },
  { id: 'shivajinagar', name: 'Shivajinagar', lat: 18.5314, lng: 73.8446 },
  { id: 'koregaon', name: 'Koregaon Park', lat: 18.5362, lng: 73.8939 },
  { id: 'kothrud', name: 'Kothrud', lat: 18.5074, lng: 73.8077 },
]

function message(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong. Please retry.' }
function isAbort(error: unknown) { return error instanceof DOMException && error.name === 'AbortError' }

export default function App() {
  const [health, setHealth] = useState<Health | null>(null), [healthError, setHealthError] = useState(false), [infoOpen, setInfoOpen] = useState(false)
  const [query, setQuery] = useState(''), [places, setPlaces] = useState<Place[]>([]), [searching, setSearching] = useState(false), [searchDone, setSearchDone] = useState(false)
  const [focus, setFocus] = useState<Place | null>(null), [panoramas, setPanoramas] = useState<Panorama[]>([]), [loadingPanos, setLoadingPanos] = useState(false), [lookedUp, setLookedUp] = useState(false), [truncated, setTruncated] = useState(false)
  const [selected, setSelected] = useState<Panorama | null>(null), [notice, setNotice] = useState('')
  const [analysis, setAnalysis] = useState<PanoramaAnalysis | null>(null), [scanning, setScanning] = useState(false), [scanError, setScanError] = useState(''), [activeDetection, setActiveDetection] = useState<PanoramaDetection | null>(null)
  const [retry, setRetry] = useState(0)
  const viewerColumn = useRef<HTMLDivElement>(null), searchAbort = useRef<AbortController | null>(null), panoAbort = useRef<AbortController | null>(null), scanAbort = useRef<AbortController | null>(null)
  const searchSerial = useRef(0), panoSerial = useRef(0), scanSerial = useRef(0), selectedId = useRef('')

  const refreshHealth = useCallback(() => { api.health().then(h => { setHealth(h); setHealthError(false) }).catch(() => setHealthError(true)) }, [])
  useEffect(() => { refreshHealth(); return () => { searchAbort.current?.abort(); panoAbort.current?.abort(); scanAbort.current?.abort() } }, [refreshHealth])
  const resetScan = useCallback(() => { scanSerial.current++; scanAbort.current?.abort(); setScanning(false); setAnalysis(null); setActiveDetection(null); setScanError('') }, [])
  const inspectDetection = useCallback((d: PanoramaDetection) => setActiveDetection({ ...d }), [])
  const selectPanorama = useCallback((p: Panorama) => {
    if (selectedId.current !== p.id) resetScan()
    selectedId.current = p.id; setSelected(p)
    if (window.matchMedia('(max-width: 850px)').matches) viewerColumn.current?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start' })
  }, [resetScan])
  const onViewerImage = useCallback((p: Panorama) => {
    if (!selectedId.current) return
    if (selectedId.current !== p.id) resetScan()
    selectedId.current = p.id; setSelected(previous => previous?.id === p.id ? { ...previous, ...p } : p)
  }, [resetScan])

  const lookup = useCallback(async (place: Place) => {
    searchSerial.current++; searchAbort.current?.abort(); setSearching(false)
    resetScan(); selectedId.current = ''; setSelected(null)
    panoAbort.current?.abort(); const controller = new AbortController(); panoAbort.current = controller
    const sequence = ++panoSerial.current
    setFocus(place); setQuery(place.name.split(',')[0]); setPlaces([]); setSearchDone(false); setLoadingPanos(true); setNotice(''); setPanoramas([]); setLookedUp(false); setTruncated(false)
    try {
      const result = await api.panoramas(place.lat, place.lng, controller.signal)
      if (sequence !== panoSerial.current) return
      setPanoramas(result.panoramas); setTruncated(result.truncated); setLookedUp(true)
    } catch (error) { if (!isAbort(error) && sequence === panoSerial.current) setNotice(message(error)) }
    finally { if (sequence === panoSerial.current) setLoadingPanos(false) }
  }, [resetScan])
  const onMapPoint = useCallback((lat: number, lng: number) => { void lookup({ id: `${lat},${lng}`, name: 'Selected map point', lat, lng }) }, [lookup])
  const submitSearch = async (event: React.FormEvent) => {
    event.preventDefault(); if (query.trim().length < 2) return
    searchAbort.current?.abort(); const controller = new AbortController(); searchAbort.current = controller
    const sequence = ++searchSerial.current
    setSearching(true); setNotice(''); setPlaces([]); setSearchDone(false)
    try {
      const result = await api.search(query.trim(), controller.signal)
      if (sequence === searchSerial.current) {
        if (result.places.length === 1) void lookup(result.places[0])
        else { setPlaces(result.places); setSearchDone(true) }
      }
    } catch (error) { if (!isAbort(error) && sequence === searchSerial.current) setNotice(message(error)) }
    finally { if (sequence === searchSerial.current) setSearching(false) }
  }
  const configured = Boolean(health?.checks.model && health?.checks.mapillary && health?.checks.shared_cache)
  const browserToken = Boolean(import.meta.env.VITE_MAPILLARY_CLIENT_TOKEN)
  const supported = Boolean(selected?.is_pano && selected.lat >= 18.40 && selected.lat <= 18.70 && selected.lng >= 73.70 && selected.lng <= 74.05)
  const unavailable = healthError ? 'Litter detection is unavailable while the service is offline.' : !health ? 'Checking litter detection availability…' : !configured ? 'Litter markings are unavailable until the trained model and service connections are ready.' : !browserToken ? 'Street imagery is unavailable until the image connection is ready.' : selected && !supported ? 'Litter detection is available only for panoramas inside the Pune demo area.' : ''

  useEffect(() => {
    if (!selected?.id || !supported || !configured || !browserToken || healthError) { resetScan(); return }
    const sequence = ++scanSerial.current, imageId = selected.id
    const controller = new AbortController(); scanAbort.current = controller
    setScanning(true); setScanError(''); setAnalysis(null); setActiveDetection(null)
    api.analyzePanorama(imageId, controller.signal).then(result => {
      if (controller.signal.aborted || sequence !== scanSerial.current || selectedId.current !== imageId) return
      if (result.image_id !== imageId) throw new Error('The results did not match this photograph. Please retry.')
      setAnalysis(result); setActiveDetection(result.detections[0] ?? null)
    }).catch(error => {
      if (!controller.signal.aborted && !isAbort(error) && sequence === scanSerial.current) setScanError(message(error))
    }).finally(() => { if (sequence === scanSerial.current) setScanning(false) })
    return () => { controller.abort(); scanSerial.current++ }
  }, [selected?.id, supported, configured, browserToken, healthError, health?.model_version, retry, resetScan])

  const nearest = panoramas[0]

  return <div className="app-shell">
    <header className="site-header">
      <a className="brand" href="/" aria-label="GeoCleanAI home"><span className="brand-symbol"><Leaf size={23} strokeWidth={1.8} /></span><span>GeoClean<span className="brand-ai">AI</span></span><span className="brand-divider"/><span className="brand-caption">STREETS WORTH CARING FOR</span></a>
      <nav aria-label="Main navigation"><a href="#explore" className="nav-active">Explore Pune</a><button onClick={() => setInfoOpen(true)}>How it works <ArrowUpRight size={13}/></button></nav>
      <span className="project-badge"><span className="live-dot" /> COLLEGE RESEARCH PROJECT</span>
    </header>

    <main id="explore">
      <section className="intro">
        <div><div className="intro-kicker"><span /> SMALL OBSERVATIONS. CLEANER STREETS.</div><h1>A clearer view of <span>Pune.</span></h1><p>Find a place. Open its street view. Explore automatically marked litter.</p></div>
        <div className="location-stamp"><MapPin size={17}/><div><strong>Pune, Maharashtra</strong><span>18.5204° N &nbsp; 73.8567° E</span></div><span className="india-dot"/></div>
      </section>

      <section className="explore-toolbar" aria-label="Location search">
        <div className="search-block"><form onSubmit={submitSearch} className="search-form"><Search size={19}/><input aria-label="Search Pune" placeholder="Search a street, neighbourhood or landmark…" value={query} onChange={e => { setQuery(e.target.value); setSearchDone(false); setPlaces([]); searchSerial.current++; searchAbort.current?.abort(); setSearching(false) }} maxLength={150}/><Button type="submit" disabled={searching || query.trim().length < 2} size="sm">{searching ? <LoaderCircle className="animate-spin"/> : <ArrowRight/>}<span className="sr-only">Search</span></Button></form>
          {(places.length > 0 || searchDone) && <div className="search-results" aria-live="polite">{places.length ? places.map(p => <button key={p.id} onClick={() => { setQuery(p.name.split(',')[0]); void lookup(p) }}><MapPin size={16}/><span>{p.name}</span><ArrowUpRight size={14}/></button>) : <p>No matching places in the Pune demo area. Try a nearby landmark.</p>}</div>}
        </div>
        <div className="area-shortcuts"><span>EXPLORE</span>{areas.map(area => <button key={area.id} onClick={() => { void lookup(area) }}>{area.name}<ArrowUpRight size={12}/></button>)}</div>
        <span className="filter-chip"><SlidersHorizontal size={14}/> Panoramas only</span>
      </section>

      {(healthError || health?.status === 'setup_required' || !browserToken) && <div className="setup-banner" role="status"><CircleHelp size={17}/><p>{healthError ? 'The API is not responding yet. The map is available while the service starts.' : !browserToken || !health?.checks.mapillary ? 'Street imagery is not connected yet. You can still explore the Pune map.' : !health?.checks.model ? 'Street exploration is available. Automatic litter markings will appear when the trained model is ready.' : 'A service connection still needs setup before all features are available.'}</p><button onClick={() => { refreshHealth(); setInfoOpen(true) }}>View status <ArrowUpRight size={13}/></button></div>}
      {notice && <div className="notice" role="alert"><CircleHelp size={17}/><span>{notice}</span><button aria-label="Dismiss notice" onClick={() => setNotice('')}><X size={16}/></button></div>}

      <div className="workspace">
        <div className="map-column"><Suspense fallback={<div className="panel panel-loading">Loading map…</div>}><MapPanel panoramas={panoramas} selected={selected} focus={focus} onPoint={onMapPoint} onSelect={selectPanorama}/></Suspense>
          {focus && <section className="location-card" aria-label="Selected location">
            <div className="location-card-title"><MapPin size={20}/><div><span>YOUR PLACE</span><h2>{focus.name}</h2><p>{focus.lat.toFixed(5)}° N, {focus.lng.toFixed(5)}° E</p></div></div>
            <p>{loadingPanos ? 'Finding nearby street photographs…' : nearest ? `${panoramas.length} nearby street ${panoramas.length === 1 ? 'view' : 'views'}${truncated ? ' in this subset' : ''}. Nearest photo: ${nearest.distance_m ?? 0} m away.` : lookedUp ? 'No street photographs found nearby. Your place is still marked on the map.' : 'Street photo availability could not be checked.'}</p>
            {nearest ? <><p>Nearest photo captured {nearest.captured_at ? new Date(nearest.captured_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'on an unavailable date'}. Photos show past conditions.</p><Button onClick={() => selectPanorama(nearest)} disabled={!browserToken}>Open street view <ArrowUpRight size={16}/></Button>{!browserToken && <p>Street imagery is not connected yet.</p>}</> : !loadingPanos && !lookedUp && <Button variant="outline" onClick={() => void lookup(focus)}>Retry nearby photos</Button>}
          </section>}
          <section className="nearby-panel" aria-label="Available panoramas"><div className="nearby-heading"><span>Nearby street views</span><span>{loadingPanos ? 'Searching…' : lookedUp ? `${panoramas.length} available` : 'Not checked'}</span></div>
            {loadingPanos ? <div className="nearby-empty"><LoaderCircle className="animate-spin" size={18}/> Looking within 500 metres…</div> : panoramas.length ? <><div className="panorama-list">{panoramas.map(p => <button key={p.id} className={selected?.id === p.id ? 'panorama-card active' : 'panorama-card'} onClick={() => selectPanorama(p)}><div className="panorama-thumb">{p.thumbnail_url ? <img src={p.thumbnail_url} alt="Street panorama preview" loading="lazy"/> : <MapPin size={20}/>}</div><div><strong>{p.distance_m ?? 0} m away</strong><span>{p.captured_at ? new Date(p.captured_at).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }) : 'Date unavailable'}</span></div><ArrowUpRight size={16}/></button>)}</div>{truncated && <p className="small-note">A subset is shown. Select a closer map point to explore more images.</p>}</> : <div className="nearby-empty"><Crosshair size={19}/><span>{lookedUp ? 'No panoramas found within 500 m. Try another point nearby.' : 'Select a map point or an area above to check image coverage.'}</span></div>}
          </section>
        </div>
        <div className="viewer-column" ref={viewerColumn}>
          <Suspense fallback={<div className="panel panel-loading">Loading street viewer…</div>}>
            <StreetViewer selected={selected} analysis={analysis} activeDetection={activeDetection} scanning={scanning} unavailable={unavailable} onImage={onViewerImage} onDetection={inspectDetection}/>
          </Suspense>
          <ResultsPanel selected={selected} analysis={analysis} scanning={scanning} error={scanError} unavailable={unavailable} activeDetection={activeDetection} onDetection={inspectDetection} onRetry={() => setRetry(value => value + 1)}/>
        </div>
      </div>

      {Boolean(health?.samples.length) && <section className="verified-samples"><h2>Verified presentation locations</h2>{health!.samples.map(p => <Button key={p.id} variant="outline" onClick={() => selectPanorama(p)}>Open photo {p.id}<ArrowUpRight/></Button>)}</section>}
      <section className="principles"><div><span><RotateIcon/></span><section><h3>Real streets. Real context.</h3><p>Explore existing street photographs, wherever panoramic coverage is available.</p></section></div><div><span><Sparkles size={20}/></span><section><h3>AI lends a second pair of eyes.</h3><p>A model trained for litter offers suggestions for you to inspect.</p></section></div><div><span><Clock3 size={20}/></span><section><h3>A moment in time.</h3><p>Every photo tells a past story. Check its date before drawing conclusions.</p></section></div></section>
    </main>
    <footer><span><Leaf size={15}/> GeoCleanAI <span className="footer-dot">·</span> Built for a cleaner tomorrow.</span><div><a href="https://www.mapillary.com/" target="_blank" rel="noreferrer">Mapillary <ExternalLink size={11}/></a><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a><button onClick={() => setInfoOpen(true)}><ShieldCheck size={13}/> About this prototype</button></div></footer>
    <InfoDialog open={infoOpen} onOpenChange={setInfoOpen} health={health}/>
  </div>
}
function RotateIcon() { return <MapPin size={20}/> }
