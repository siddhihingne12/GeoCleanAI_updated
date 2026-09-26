import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
await fs.mkdir('artifacts', { recursive: true })
const browser = await chromium.launch({ channel: 'msedge', headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1050 } })
const errors = []
page.on('pageerror', error => errors.push(error.message))
page.on('console', entry => { if (entry.type() === 'error') errors.push(entry.text().slice(0,250)) })
page.on('requestfailed', request => { const u = new URL(request.url()); errors.push(`${u.hostname}${u.pathname}: ${request.failure()?.errorText}`) })
await page.goto(process.argv[2] || 'http://127.0.0.1:5173', { waitUntil: 'domcontentloaded' })
await page.getByTestId('map-container').waitFor({ state: 'visible', timeout: 20000 })
await page.getByTestId('street-viewer').waitFor({ state: 'visible', timeout: 20000 })
await page.locator('.map-loading').waitFor({ state: 'hidden', timeout: 20000 }).catch(() => {})
await page.getByRole('heading', { name: 'A clearer view of Pune.' }).waitFor({ state: 'visible' })
await page.waitForTimeout(1000)
await page.screenshot({ path: 'artifacts/live-desktop.png', fullPage: true })
console.log(JSON.stringify({ title: await page.title(), textLength: (await page.locator('body').innerText()).length, mapLoading: await page.locator('.map-loading').count(), mapNotice: await page.locator('.map-notice').allTextContents(), errors }, null, 2))
await browser.close()
