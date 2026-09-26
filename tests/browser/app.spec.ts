import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/health', route => route.fulfill({ json: { status: 'setup_required', checks: { model: false, mapillary: false, shared_cache: true, search: false }, model_version: null, samples: [] } }))
})

test('honest setup state and accessible project information', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.getByTestId('map-container')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'A clearer view of Pune.' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Scan this view' })).toHaveCount(0)
  await expect(page.getByText('UNAVAILABLE', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'How it works' }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'How it works' })).toBeFocused()
  expect(errors).toEqual([])
  await page.screenshot({ path: 'artifacts/desktop.png', fullPage: true })
})

test('search only runs on submission and missing coverage stays distinct', async ({ page }) => {
  let requests = 0
  await page.route('**/api/search?*', route => { requests++; return route.fulfill({ json: { places: [{ id: 'pune', name: 'Pune test landmark', lat: 18.52, lng: 73.85 }] } }) })
  await page.route('**/api/panoramas?*', route => route.fulfill({ json: { panoramas: [], truncated: false } }))
  await page.goto('/')
  await page.getByRole('textbox', { name: 'Search Pune' }).fill('Pune')
  await page.waitForTimeout(300)
  expect(requests).toBe(0)
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Selected location' })).toContainText('Pune test landmark')
  await expect(page.getByRole('img', { name: 'Selected place: Pune test landmark' })).toBeAttached()
  await expect(page.getByText('No panoramas found within 500 m. Try another point nearby.')).toBeVisible()
  await expect(page.getByText('UNAVAILABLE', { exact: true })).toBeVisible()
  expect(requests).toBe(1)
})

test('provider failures explain the failure rather than reporting a clean street', async ({ page }) => {
  await page.route('**/api/panoramas?*', route => route.fulfill({ status: 503, json: { error: { code: 'mapillary_unavailable', message: 'Could not reach Mapillary. Please retry.' } } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Shivajinagar' }).click()
  await expect(page.getByRole('alert')).toContainText('Could not reach Mapillary')
  await expect(page.getByText('No panoramas found within 500 m. Try another point nearby.')).not.toBeVisible()
})

test('older lookup cannot replace the latest location', async ({ page }) => {
  await page.route('**/api/panoramas?*', async route => {
    const isFirst = route.request().url().includes('18.5314')
    if (isFirst) await new Promise(resolve => setTimeout(resolve, 700))
    await route.fulfill({ json: { panoramas: isFirst ? [{ id: '1', lat: 18.53, lng: 73.84, is_pano: true, creator: 'TEST FIXTURE', captured_at: 0 }] : [], truncated: false } }).catch(() => {})
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Shivajinagar' }).click()
  await page.getByRole('button', { name: 'Kothrud' }).click()
  await expect(page.getByText('No panoramas found within 500 m. Try another point nearby.')).toBeVisible()
  await page.waitForTimeout(850)
  await expect(page.getByText('0 available', { exact: true })).toBeVisible()
})

test('mobile layout remains within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByTestId('map-container')).toBeVisible()
  await expect(page.getByText('Automatic litter markings', { exact: true })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow).toBe(false)
  await page.screenshot({ path: 'artifacts/mobile.png', fullPage: true })
})
