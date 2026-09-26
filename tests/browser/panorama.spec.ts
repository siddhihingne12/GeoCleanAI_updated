import { test, expect, type Page } from '@playwright/test'
import { readFile } from 'node:fs/promises'

const place = { id: 'pune', name: 'Pune test landmark', lat: 18.52, lng: 73.85 }
const photo = (id: string, distance_m = 20) => ({ id, lat: 18.52, lng: 73.85, is_pano: true, captured_at: 1704067200000, creator: 'TEST FIXTURE', distance_m })
const preview = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640"><rect width="640" height="640" fill="#eaf1e4"/><text x="20" y="40">TEST FIXTURE — not a street photograph</text></svg>')
const result = (id = '123', empty = false) => ({
  image_id: id, model_version: 'TEST-ONLY', analysis_version: 'test', captured_at: 1704067200000, elapsed_ms: 1500, cached: false,
  views: ['front', 'right', 'back', 'left', 'up', 'down'].map(id => ({ id, preview, view: { origin: [0, 0, 1], right: [1, 0, 0], down: [0, -1, 0], aspect: 1 } })),
  detections: empty ? [] : [
    { id: 'litter-1', view_id: 'front', label: 'litter', confidence: .9, box: [.2, .3, .4, .5], tag: [.45, .55] },
    { id: 'litter-2', view_id: 'back', label: 'litter', confidence: .8, box: [.6, .6, .7, .7], tag: [.99, .65] },
  ],
})

test.beforeEach(async ({ page }) => {
  // Supply a test token only to intercepted dev modules, never to production files.
  await page.route(/\/src\/(App\.tsx|components\/StreetViewer\.tsx)(\?|$)/, async route => {
    const response = await route.fetch()
    const body = (await response.text()).replaceAll('import.meta.env.VITE_MAPILLARY_CLIENT_TOKEN', '"TEST-ONLY"')
    await route.fulfill({ response, body })
  })
  const viewerFixture = await readFile('tests/browser/fixtures/mapillary.js', 'utf8')
  await page.route(/\/node_modules\/\.vite\/deps\/mapillary-js\.js/, route => route.fulfill({ contentType: 'application/javascript', body: viewerFixture }))
  await page.route('https://tiles.openfreemap.org/styles/liberty', route => route.fulfill({ json: { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#eaf1e4' } }] } }))
  await page.route('**/api/health', route => route.fulfill({ json: { status: 'ready', checks: { model: true, mapillary: true, shared_cache: true, search: true }, model_version: 'TEST-ONLY', samples: [] } }))
  await page.route('**/api/search?*', route => route.fulfill({ json: { places: [place] } }))
  await page.route('**/api/panoramas?*', route => route.fulfill({ json: { panoramas: [photo('123'), photo('456', 60)], truncated: false } }))
})

async function search(page: Page) {
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Search Pune' }).fill('Pune')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected location' })).toContainText(place.name)
}

test('search pins the place; opening automatically marks litter and links the correct evidence', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  let requests = 0
  await page.route('**/api/analyze-panorama', async route => {
    requests++
    expect(route.request().postDataJSON()).toEqual({ image_id: '123' })
    await new Promise(resolve => setTimeout(resolve, 250))
    await route.fulfill({ json: result() })
  })
  await page.addInitScript(() => { (window as any).__testViewerDelay = 500 })
  await search(page)
  await expect(page.getByRole('img', { name: `Selected place: ${place.name}` })).toBeVisible()
  expect(requests).toBe(0)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.getByRole('region', { name: 'AI results' })).toContainText('Finding litter')
  const first = page.getByRole('button', { name: 'Litter 1 · 90%', exact: true })
  const second = page.getByRole('button', { name: 'Litter 2 · 80%', exact: true })
  await expect(first).toBeVisible()
  await expect(first).toHaveAttribute('data-tag', '[0.45,0.55]')
  await expect(page.locator('.scan-preview')).toHaveAttribute('data-view-id', 'front')
  await expect(page.locator('.scan-preview .detection-box')).toHaveCount(1)
  await page.getByRole('button', { name: 'Show suspected litter 2' }).click()
  await expect(page.getByTestId('street-viewer')).toHaveAttribute('data-center', '[0.99,0.65]')
  await expect(page.locator('.scan-preview')).toHaveAttribute('data-view-id', 'back')
  await expect(page.locator('.scan-preview .detection-box')).toHaveAttribute('data-detection-id', 'litter-2')
  await first.click()
  await expect(page.getByRole('button', { name: 'Show suspected litter 1' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('.scan-preview')).toHaveAttribute('data-view-id', 'front')
  await second.click()
  await page.getByRole('button', { name: 'Expand street view' }).click()
  await expect.poll(() => page.evaluate(() => Boolean(document.fullscreenElement))).toBe(true)
  await expect(second).toBeVisible()
  await page.evaluate(() => document.exitFullscreen())
  // Simulated camera movement and resize do not trigger inference again.
  await page.evaluate(() => (window as any).__testViewer.setCenter([.1, .5]))
  await page.setViewportSize({ width: 1024, height: 800 })
  await expect(second).toBeVisible()
  await page.getByRole('button', { name: 'Show suspected litter 2' }).click()
  await expect(page.getByTestId('street-viewer')).toHaveAttribute('data-center', '[0.99,0.65]')
  expect(requests).toBe(1)
  expect(errors).toEqual([])
  await page.screenshot({ path: 'artifacts/panorama-test-desktop.png', fullPage: true })
})

test('multiple search matches require selection and no matches keep the map usable', async ({ page }) => {
  await page.route('**/api/search?*', route => route.fulfill({ json: { places: [place, { ...place, id: 'other', name: 'Other Pune landmark' }] } }))
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Search Pune' }).fill('Pune')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected location' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Other Pune landmark' }).click()
  await expect(page.getByRole('img', { name: 'Selected place: Other Pune landmark' })).toBeVisible()
  await page.route('**/api/search?*', route => route.fulfill({ json: { places: [] } }))
  await page.getByRole('textbox', { name: 'Search Pune' }).fill('Unknown')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByText('No matching places in the Pune demo area. Try a nearby landmark.')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Selected place: Other Pune landmark' })).toBeVisible()
})

test('new location clears the photo and late analysis cannot restore its results', async ({ page }) => {
  let requested = false
  await page.route('**/api/analyze-panorama', async route => {
    requested = true
    await new Promise(resolve => setTimeout(resolve, 700))
    await route.fulfill({ json: result() }).catch(() => {})
  })
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect.poll(() => requested).toBe(true)
  await page.getByRole('button', { name: 'Kothrud', exact: true }).click()
  await page.waitForTimeout(850)
  await expect(page.getByRole('region', { name: 'Selected location' })).toContainText('Kothrud')
  await expect(page.getByRole('button', { name: 'Show suspected litter 1' })).toHaveCount(0)
  await expect(page.locator('.image-credit')).toHaveCount(0)
  await expect(page.getByText('OPEN A STREET VIEW', { exact: true })).toBeVisible()
})

test('navigating between photos analyses each and displays cached reopening', async ({ page }) => {
  const counts: Record<string, number> = {}
  await page.route('**/api/analyze-panorama', route => {
    const id = route.request().postDataJSON().image_id
    counts[id] = (counts[id] || 0) + 1
    return route.fulfill({ json: { ...result(id), cached: counts[id] > 1 } })
  })
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Litter 1 · 90%', exact: true })).toBeVisible()
  // Mapillary sequence navigation sends the same image event as opening a photo.
  await page.evaluate(() => (window as any).__testViewer.moveTo('456'))
  await expect(page.locator('.image-credit a')).toHaveAttribute('href', /pKey=456$/)
  await expect(page.getByText('ANALYSIS COMPLETE', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.getByText(/Saved result/)).toBeVisible()
  expect(counts).toEqual({ '123': 2, '456': 1 })
})

test('a late photo event and analysis cannot replace the newly opened photo', async ({ page }) => {
  let firstRequested = false
  await page.route('**/api/analyze-panorama', async route => {
    const id = route.request().postDataJSON().image_id
    if (id === '123') { firstRequested = true; await new Promise(resolve => setTimeout(resolve, 600)) }
    await route.fulfill({ json: result(id, id === '456') }).catch(() => {})
  })
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect.poll(() => firstRequested).toBe(true)
  await page.evaluate(() => { (window as any).__testViewerDelay = 350 })
  await page.getByRole('button', { name: /60 m away/ }).click()
  await page.evaluate(() => (window as any).__testViewer.listeners.image?.({ image: { id: '123', originalLngLat: { lat: 18.52, lng: 73.85 }, cameraType: 'spherical', capturedAt: 1704067200000, creatorUsername: 'TEST FIXTURE' } }))
  await expect(page.locator('.image-credit a')).toHaveAttribute('href', /pKey=456$/)
  await expect(page.getByText(/No litter detected in this panorama/)).toBeVisible()
  await page.waitForTimeout(700)
  await expect(page.locator('.image-credit a')).toHaveAttribute('href', /pKey=456$/)
  await expect(page.getByRole('button', { name: 'Show suspected litter 1' })).toHaveCount(0)
})

test('a delayed search cannot replace a place chosen from the map shortcuts', async ({ page }) => {
  let requested = false
  await page.route('**/api/search?*', async route => {
    requested = true
    await new Promise(resolve => setTimeout(resolve, 500))
    await route.fulfill({ json: { places: [place] } }).catch(() => {})
  })
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Search Pune' }).fill('Pune')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect.poll(() => requested).toBe(true)
  await page.getByRole('button', { name: 'Kothrud', exact: true }).click()
  await page.waitForTimeout(650)
  await expect(page.getByRole('region', { name: 'Selected location' })).toContainText('Kothrud')
  await expect(page.getByRole('img', { name: 'Selected place: Kothrud' })).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Search Pune' })).toHaveValue('Kothrud')
})

test('busy and timeout states allow retry and never imply a clean street', async ({ page }) => {
  let attempts = 0
  await page.route('**/api/analyze-panorama', route => {
    attempts++
    if (attempts === 1) return route.fulfill({ status: 429, json: { error: { code: 'busy', message: 'Another scan is running. Please try again shortly.' } } })
    if (attempts === 2) return route.fulfill({ status: 504, json: { error: { code: 'analysis_timeout', message: 'Litter detection took too long. Please retry.' } } })
    return route.fulfill({ json: result('123', true) })
  })
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.getByText('DETECTION FAILED', { exact: true })).toBeVisible()
  await expect(page.getByText(/No litter detected/)).toHaveCount(0)
  await page.getByRole('button', { name: 'Retry detection' }).click()
  await expect(page.getByText('Litter detection took too long. Please retry.')).toBeVisible()
  await page.getByRole('button', { name: 'Retry detection' }).click()
  await expect(page.getByText(/No litter detected in this panorama/)).toBeVisible()
  expect(attempts).toBe(3)
})

test('missing model allows street exploration without fabricated markings', async ({ page }) => {
  let requests = 0
  await page.route('**/api/health', route => route.fulfill({ json: { status: 'setup_required', checks: { model: false, mapillary: true, shared_cache: true, search: true }, model_version: null, samples: [] } }))
  await page.route('**/api/analyze-panorama', route => { requests++; return route.abort() })
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.locator('.image-credit')).toContainText('TEST FIXTURE')
  await expect(page.getByText('UNAVAILABLE', { exact: true })).toBeVisible()
  await expect(page.getByText(/No litter detected/)).toHaveCount(0)
  expect(requests).toBe(0)
})

test('mobile opening scrolls to the viewer and results fit the screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.route('**/api/analyze-panorama', route => route.fulfill({ json: result() }))
  await search(page)
  await page.getByRole('button', { name: 'Open street view', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Litter 1 · 90%', exact: true })).toBeVisible()
  await expect.poll(() => page.locator('.viewer-column').evaluate(element => Math.abs(element.getBoundingClientRect().top - 18))).toBeLessThan(5)
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await page.screenshot({ path: 'artifacts/panorama-test-mobile.png', fullPage: true })
})
