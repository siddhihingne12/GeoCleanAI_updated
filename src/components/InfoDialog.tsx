import * as Dialog from '@radix-ui/react-dialog'
import { useRef } from 'react'
import { Check, Circle, ExternalLink, X } from 'lucide-react'
import type { Health } from '../types'
import { Button } from './ui/button'

export function InfoDialog({ open, onOpenChange, health }: { open: boolean; onOpenChange: (v: boolean) => void; health: Health | null }) {
  const opener = useRef<HTMLElement | null>(null)
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal>
    <Dialog.Overlay className="dialog-overlay" />
    <Dialog.Content className="dialog-content" onOpenAutoFocus={() => { opener.current = document.activeElement as HTMLElement }} onCloseAutoFocus={event => { event.preventDefault(); opener.current?.focus() }}>
      <Dialog.Title className="dialog-title">AI-Powered Illegal Garbage Dumping Detection</Dialog.Title>
      <Dialog.Description className="dialog-description">GeoClean AI is an intelligent monitoring system that detects waste accumulation, identifies dumping hotspots, and tracks severity across Pune streets using Grounding DINO, SAM 2, and YOLO models.</Dialog.Description>
      <div className="how-steps">{[['01', 'Find your place', 'Search Pune and see the chosen place pinned on the map. Nearby street photographs appear where coverage is available.'], ['02', 'Open street view', 'Open the nearest 360° photograph or choose another camera location. Check its capture date; photos show past conditions.'], ['03', 'AI waste detection', 'Grounding DINO detects garbage piles using text prompts. SAM 2 segments the waste region. YOLO serves as a baseline model. Select a marker to inspect evidence.'], ['04', 'Hotspot analysis', 'Nearby detections are clustered into hotspots. Each hotspot is scored by waste area, confidence, recency, and repeat observations. Track severity over time.']].map(([number, title, copy]) => <div key={number}><span>{number}</span><section><h3>{title}</h3><p>{copy}</p></section></div>)}</div>
      <details className="connection-details"><summary>Connection details</summary><div className="connection-list">{Object.entries(health?.checks ?? { api: false }).map(([name, ready]) => <p key={name}>{ready ? <Check size={15}/> : <Circle size={15}/>}<span>{name.replaceAll('_', ' ')}</span><strong>{ready ? 'Configured' : 'Not configured'}</strong></p>)}</div><p>Checks confirm configuration, not provider availability. The AI models (Grounding DINO, SAM 2, YOLO) and service connections are required for full scanning capability.</p></details>
      <div className="info-models"><strong>AI Models:</strong> Grounding DINO (text-prompted detection) · SAM 2 (waste segmentation) · YOLO (baseline)</div>
      <a className="source-link" href="https://www.mapillary.com/" target="_blank" rel="noreferrer">Street imagery by Mapillary <ExternalLink size={13}/></a>
      <Dialog.Close asChild><Button size="icon" variant="ghost" className="dialog-close" aria-label="Close project information"><X /></Button></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>
}
