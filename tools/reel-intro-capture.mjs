// Captures one 1080x1920 still per shot named in tools/reel-intro-script.json,
// by driving a real browser over the real pages. The film therefore shows the
// site as it actually is on the day it is cut - not a mock-up that drifts.
//
//   usage: node tools/reel-intro-capture.mjs <base-url> <out-dir>
//
// The viewport is 540x960 at 2x, which is a phone's shape: the reel is made to
// be watched on a phone, and so is the site, so what the film shows is what the
// viewer will meet when they open it.
//
// Each shot names an element to bring into view rather than a pixel offset.
// A page can grow a paragraph without the film silently pointing at nothing -
// a selector that stops matching throws here instead.
import pw from '/home/sverma/.npm/_npx/9833c18b2d85bc59/node_modules/playwright/index.js';
import { copyFileSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, '..');

const base = process.argv[2] || 'http://127.0.0.1:8099';
const out = process.argv[3];
if (!out) { console.error('usage: node tools/reel-intro-capture.mjs <base-url> <out-dir>'); process.exit(1); }

// shot -> [path, selector to settle on, how far down the screen to put it]
const SHOTS = {
  'home-hero':        ['/hi/',             'section.hero',        0],
  'home-sahyog':      ['/hi/',             '.wrap.section:has(h2:text-is("सहयोग कैसे करें"))', 0.04],
  'daan-top':         ['/hi/daan/',        '.year-list',          0.10],
  // The roll itself lives on a year's own page, not on the दान index, and it is
  // drawn by donors.js from the JSON - hence the wait for a card, below.
  'daan-roll':        ['/hi/daan/navdurga-mahotsav-2026/', '.donor-card', 0.22],
  'karyakram':        ['/hi/karyakram/',   '.festivals',          0.10],
  'karyakram-poster': ['/hi/karyakram/',   '.posters',            0.10],
  'shiksha':          ['/hi/shiksha/',     '.scheme-list',        0.14],
  'swasthya':         ['/hi/swasthya/',    '.scheme-list',        0.14],
  'padadhikari':      ['/hi/padadhikari/', '.person-grid',        0.10],
  'gallery-photos':   ['/hi/gallery/',     '#navratri-2026',      0.06],
  'sampark':          ['/hi/sampark/',     '.contact-list',       0.14],
};

const b = await pw.chromium.launch({ executablePath: '/usr/bin/google-chrome' });
const page = await b.newPage({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 2 });

// The closing card has to be served from the site root for its /assets/ paths
// to resolve, but it must not BE a page of the site. A dot-name is skipped by
// Pages and by both of the repo's own path guards, and it is removed again
// below whatever happens here.
const cardSrc = join(here, 'reel-intro-endcard.html.in');
const cardTmp = join(siteRoot, '.reel-endcard.html');
copyFileSync(cardSrc, cardTmp);
try {

let loaded = '';
for (const [shot, [path, selector, topFraction]] of Object.entries(SHOTS)) {
  if (loaded !== path) {
    await page.goto(base + path, { waitUntil: 'networkidle' });
    loaded = path;
  }
  // Some of these pages draw themselves from JSON after load, so wait for the
  // element rather than assuming it is in the HTML.
  const target = page.locator(selector).first();
  await target.waitFor({ state: 'visible', timeout: 15000 })
    .catch(() => { throw new Error(`${shot}: nothing matches ${selector} on ${path}`); });
  // Put the element a little below the top edge rather than flush against it,
  // so the shot does not look cropped at the moment the cut lands on it. The
  // box is measured through the locator, not querySelector, so Playwright's own
  // selector engines (:has, :text-is) work for headings that carry no id.
  await target.scrollIntoViewIfNeeded();
  const box = await target.boundingBox();
  if (!box) throw new Error(`${shot}: ${selector} has no box - is it hidden?`);
  await page.evaluate(({ top, frac, h }) => window.scrollBy(0, top - h * frac),
                      { top: box.y, frac: topFraction, h: 960 });
  // Let the sticky header settle and any lazy image below the fold arrive.
  await page.waitForTimeout(700);
  await page.screenshot({ path: `${out}/${shot}.png` });
  console.log(shot, '<-', path, selector);
}

await page.goto(base + '/.reel-endcard.html', { waitUntil: 'networkidle' });
await page.waitForTimeout(900);
await page.screenshot({ path: `${out}/closing.png` });
console.log('closing <- tools/reel-intro-endcard.html.in');

} finally {
  rmSync(cardTmp, { force: true });
  await b.close();
}
