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
      <Dialog.Title className="dialog-title">A clearer view, one street at a time.</Dialog.Title>
      <Dialog.Description className="dialog-description">GeoCleanAI is a college research project exploring how computer vision can help identify visible street litter in Pune.</Dialog.Description>
      <div className="how-steps">{[['01', 'Find your place', 'Search Pune and see the chosen place pinned on the map. Nearby street photographs appear where coverage is available.'], ['02', 'Open street view', 'Open the nearest 360° photograph or choose another camera location. Check its capture date; photos show past conditions.'], ['03', 'Inspect marked litter', 'AI automatically checks all directions and marks suspected litter. Select a marker to inspect its evidence. The AI can miss objects or make mistakes.']].map(([number, title, copy]) => <div key={number}><span>{number}</span><section><h3>{title}</h3><p>{copy}</p></section></div>)}</div>
      <details className="connection-details"><summary>Connection details</summary><div className="connection-list">{Object.entries(health?.checks ?? { api: false }).map(([name, ready]) => <p key={name}>{ready ? <Check size={15}/> : <Circle size={15}/>}<span>{name.replaceAll('_', ' ')}</span><strong>{ready ? 'Configured' : 'Not configured'}</strong></p>)}</div><p>Checks confirm configuration, not provider availability. The trained model and account connections are required for scanning.</p></details>
      <a className="source-link" href="https://www.mapillary.com/" target="_blank" rel="noreferrer">Street imagery by Mapillary <ExternalLink size={13}/></a>
      <Dialog.Close asChild><Button size="icon" variant="ghost" className="dialog-close" aria-label="Close project information"><X /></Button></Dialog.Close>
    </Dialog.Content>
  </Dialog.Portal></Dialog.Root>
}
