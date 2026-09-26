// Browser integration fixture only. This module is never imported by the app.
// It exercises viewer events and marker wiring, not real image alignment.
export class PointGeometry { constructor(point) { this.point = point } }
export class SpotTag {
  constructor(id, geometry, options) { this.id = id; this.geometry = geometry; this.options = options; this.listeners = {} }
  on(event, callback) { this.listeners[event] = callback }
}
export class Viewer {
  constructor({ container }) {
    this.container = container; this.listeners = {}; this.removed = false
    this.container.style.background = '#e7efe1'
    this.label = document.createElement('p'); this.label.textContent = 'TEST FIXTURE — not a street photograph'
    this.container.append(this.label)
    this.tags = document.createElement('div'); this.container.append(this.tags)
    window.__testViewer = this
  }
  on(event, callback) { this.listeners[event] = callback }
  off(event) { delete this.listeners[event] }
  async setFilter() {}
  async moveTo(id) {
    if (window.__testViewerDelay) await new Promise(resolve => setTimeout(resolve, window.__testViewerDelay))
    if (this.removed) return
    this.current = id
    this.label.textContent = `TEST FIXTURE — photo ${id}`
    this.listeners.image?.({ image: { id, originalLngLat: { lat: 18.52, lng: 73.85 }, cameraType: 'spherical', capturedAt: 1704067200000, creatorUsername: 'TEST FIXTURE' } })
  }
  getComponent() {
    return {
      removeAll: () => this.tags.replaceChildren(),
      add: tags => tags.forEach(tag => {
        const button = document.createElement('button')
        button.textContent = tag.options.text
        button.dataset.tag = JSON.stringify(tag.geometry.point)
        button.dataset.color = String(tag.options.color)
        button.style.cssText = 'padding:12px; margin:8px; background:#d8f3a5; border:1px solid #245743; border-radius:8px;'
        button.addEventListener('click', () => tag.listeners.click?.())
        this.tags.append(button)
      }),
    }
  }
  setCenter(point) { this.container.dataset.center = JSON.stringify(point) }
  resize() {}
  remove() { this.removed = true; this.container.replaceChildren() }
}
