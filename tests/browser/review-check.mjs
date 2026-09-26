// Standalone browser check; writes only to a temporary fixture, never human labels.
import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdtemp, mkdir, writeFile, readFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

await mkdir('artifacts', { recursive: true });
const folder = await mkdtemp(path.resolve('artifacts/review-fixture-'));
await mkdir(path.join(folder, 'images'));
const pixel = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aWZkAAAAASUVORK5CYII=', 'base64');
const views = [0, 1, 2].map(i => ({ file_name: `${i}_front.png`, image_id: String(i), view_id: 'front', capture_date: '2026-01-01', contributor: 'Browser test fixture', original_resolution: true, sequence: `test-${i}` }));
await Promise.all(views.map(v => writeFile(path.join(folder, 'images', v.file_name), pixel)));
await writeFile(path.join(folder, 'manifest.json'), JSON.stringify({ analysis_version: 'test', views }));
const server = spawn(path.resolve('.venv/Scripts/python.exe'), ['-m', 'training.review_server', '--data', folder, '--port', '8766'], { windowsHide: true, stdio: 'ignore' });
let browser;
try {
  let ready = false;
  for (let n = 0; n < 40; n++) {
    try { if ((await fetch('http://127.0.0.1:8766/api/views')).ok) { ready = true; break; } } catch {}
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  assert(ready, 'Review fixture server did not start');
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1360, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('dialog', dialog => dialog.accept());
  await page.goto('http://127.0.0.1:8766');
  await page.waitForFunction(() => document.querySelector('#photo').naturalWidth > 0);
  await page.locator('#reviewer').fill('Browser test only');
  const area = await page.locator('#overlay').boundingBox();
  await page.mouse.move(area.x + area.width * .1, area.y + area.height * .2);
  await page.mouse.down();
  await page.mouse.move(area.x + area.width * .4, area.y + area.height * .6, { steps: 8 });
  await page.mouse.up();
  assert(await page.locator('#clean').isDisabled());
  await page.locator('#save').click();
  await page.getByText('Saved: litter.', { exact: false }).waitFor();
  await page.reload();
  // Reload selects the next unreviewed image; return to the saved one.
  await page.locator('#choose').selectOption('0');
  await page.getByRole('button', { name: 'Remove litter box 1', exact: true }).waitFor();
  assert.equal(await page.locator('#overlay rect').count(), 1);
  await page.locator('#next').click();
  await page.locator('#clean').click();
  await page.getByText('Saved: clean.', { exact: false }).waitFor();
  await page.locator('#next').click();
  await page.locator('#notes').fill('Test fixture is intentionally unclear');
  await page.locator('#skip').click();
  await page.getByText('Saved: skip.', { exact: false }).waitFor();
  assert.match(await page.locator('#progressText').textContent(), /2 \/ 3 reviewed · 1 skipped/);
  await page.screenshot({ path: 'artifacts/review-test-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth));
  await page.screenshot({ path: 'artifacts/review-test-mobile.png', fullPage: true });
  const record = JSON.parse(await readFile(path.join(folder, 'reviews/0_front.png.json'), 'utf8'));
  record.boxes[0].forEach((v, i) => assert(Math.abs(v - [.1, .2, .4, .6][i]) < .01));
  assert.deepEqual(errors, []);
  console.log('Review browser check passed: drawing, save, reload, clean, skip, normalized boxes, desktop and mobile.');
} finally {
  if (browser) await browser.close();
  server.kill();
}
