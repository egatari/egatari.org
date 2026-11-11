// Checks /gallery/play/ in an assembled site (after `python3 tools/gallery_files.py fetch <site>`), served the way GitHub Pages
// serves it: no security headers, the content type from the extension (.bin → application/octet-stream).
//   npm ci && npx playwright-core install chromium && node tools/test-gallery-play.mjs <site dir>
// - The vendored player is the build BUILD.json names (SHA-256 of each file), and the page's <meta> policy is BUILD.json's pageCsp.
// - Every lesson in the lock plays: its title, sandbox="allow-scripts", an opaque origin with no storage, page or network access.
// - A changed byte, an unknown id, or no id plays nothing; inside another site's frame nothing plays.
// - A lesson file opened directly is downloaded, never rendered; every gallery card links to its play page.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import { chromium } from 'playwright-core';

const site = path.resolve(process.argv[2] || '_site');
let fails = 0;
const ok = (c, m) => { console.log((c ? '  ok   ' : '  FAIL ') + m); if (!c) fails++; };
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const G = path.join(site, 'gallery');
const lock = JSON.parse(fs.readFileSync(path.join(G, 'samples.lock.json'), 'utf8'));
const build = JSON.parse(fs.readFileSync(path.join(G, 'play', 'BUILD.json'), 'utf8'));

console.log('files');
ok(Object.entries(build.sha256).every(([f, h]) => sha(fs.readFileSync(path.join(G, 'play', f))) === h), `the vendored player is Studio ${build.version} (SHA-256 of each file as in BUILD.json)`);
const page = fs.readFileSync(path.join(G, 'play', 'index.html'), 'utf8');
const metas = [...page.matchAll(/<meta http-equiv="Content-Security-Policy" content="([^"]*)">/g)];
ok(metas.length === 1 && metas[0][1] === build.pageCsp && page.indexOf(metas[0][0]) < page.indexOf('<script') && page.indexOf(metas[0][0]) < page.indexOf('<link'), 'the page carries BUILD.json\'s policy in one <meta>, before any script or style sheet');
ok(lock.lessons.every((l) => { const f = path.join(G, 'files', l.id + '.ega.bin'); return fs.existsSync(f) && sha(fs.readFileSync(f)) === l.sha256; }), `every lesson in the lock (${lock.lessons.length}) is in gallery/files/ with its SHA-256`);
const index = fs.readFileSync(path.join(G, 'index.html'), 'utf8');
ok(lock.lessons.every((l) => index.includes(`href="/gallery/play/?id=${l.id}"`)), 'every gallery card links to /gallery/play/?id=<id>');

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.woff2': 'font/woff2' };
function serve(dir) {
  const srv = http.createServer((req, res) => {
    let p = decodeURIComponent(new URL(req.url, 'http://x').pathname); if (p.endsWith('/')) p += 'index.html';
    const f = path.join(dir, ...p.split('/').filter(Boolean));
    if (!f.startsWith(dir) || !fs.existsSync(f) || fs.statSync(f).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); res.end(fs.readFileSync(f));
  });
  return new Promise((r) => srv.listen(0, '127.0.0.1', () => r({ url: `http://127.0.0.1:${srv.address().port}`, close: () => new Promise((c) => { srv.closeAllConnections(); srv.close(c); }) })));
}
const S = await serve(site);
const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
const errors = [];
// the isolation check below asks the lesson's frame to fetch the lock: those refusals are the expected result, not page errors
const isProbe = (t) => /samples\.lock\.json/.test(t) && /connect-src 'none'|Fetch API cannot load/.test(t);
async function open(base, q) {
  const c = await browser.newContext({ locale: 'ja-JP', viewport: { width: 1280, height: 800 } });
  const p = await c.newPage();
  p.on('pageerror', (e) => errors.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error' && /Content Security Policy|Refused/.test(m.text()) && !isProbe(m.text())) errors.push(m.text()); });
  await p.goto(`${base}/gallery/play/${q}`);
  await p.waitForSelector('html[data-player-ready]', { timeout: 30000 });
  return { c, p, st: () => p.evaluate(() => window.__sitePlayer.state()) };
}

console.log('play');
for (const l of lock.lessons) {
  const { c, p, st } = await open(S.url, `?id=${l.id}`);
  const fr = await p.$('#egatari-player iframe');
  const f = fr && await fr.contentFrame();
  let ready = false;
  for (let i = 0; i < 150 && f && !ready; i++) { ready = await f.evaluate(() => !!(window.DECK && DECK.ready)).catch(() => false); if (!ready) await p.waitForTimeout(100); }
  const iso = f && await f.evaluate(async () => {
    let storage = false, net = false, parentDom = false;
    try { localStorage.getItem('x'); storage = true; } catch { /* refused */ }
    try { await fetch('/gallery/samples.lock.json'); net = true; } catch { /* refused */ }
    try { parentDom = !!parent.document; } catch { /* refused */ }
    return self.origin === 'null' && !storage && !net && !parentDom;
  });
  ok((await st()).state === 'playing' && ready && (await fr.getAttribute('sandbox')) === 'allow-scripts' && (await p.textContent('[data-player-title]')) === l.title && iso,
    `${l.id}: plays (${l.title}) in an opaque origin with no storage, page or network access`);
  if (l === lock.lessons[0]) await p.screenshot({ path: path.join(os.tmpdir(), 'gallery-play.png') });
  await c.close();
}

console.log('refusals');
const bad = fs.mkdtempSync(path.join(os.tmpdir(), 'gallery-play-bad-'));
fs.cpSync(site, bad, { recursive: true });
const first = lock.lessons[0].id, fb = path.join(bad, 'gallery', 'files', first + '.ega.bin');
const b = fs.readFileSync(fb); b[b.length - 20] ^= 1; fs.writeFileSync(fb, b);
const B = await serve(bad);
for (const [base, q, state, what] of [[B.url, `?id=${first}`, 'mismatch', 'a file with one byte changed'], [S.url, '?id=not-a-sample', 'unknown', 'an id not in the lock'], [S.url, '', 'no-id', 'no id']]) {
  const { c, p, st } = await open(base, q);
  ok((await st()).state === state && !(await p.$('#egatari-player iframe')) && (await p.textContent('.sp-status')).length > 0, `${what}: nothing plays, and the page says why`);
  await c.close();
}
await B.close();

console.log('framed and direct');
const other = fs.mkdtempSync(path.join(os.tmpdir(), 'gallery-play-other-'));
fs.writeFileSync(path.join(other, 'index.html'), `<!DOCTYPE html><iframe src="${S.url}/gallery/play/?id=${first}" style="width:800px;height:600px"></iframe>`);
const O = await serve(other);
{ const c = await browser.newContext(); const p = await c.newPage();
  await p.goto(O.url + '/');
  const f = await (await p.waitForSelector('iframe')).contentFrame();
  await f.waitForSelector('html[data-player-ready]', { timeout: 30000 });
  ok((await f.evaluate(() => window.__sitePlayer.state().state)) === 'framed' && !(await f.$('#egatari-player iframe')), 'inside another site\'s frame nothing plays');
  await c.close(); }
{ const c = await browser.newContext({ acceptDownloads: true }); const p = await c.newPage();
  const dl = p.waitForEvent('download', { timeout: 15000 }).then(() => true, () => false);
  await p.goto(`${S.url}/gallery/files/${first}.ega.bin`).catch(() => {});
  ok(await dl, 'a lesson file opened directly is downloaded (application/octet-stream), not rendered');
  await c.close(); }
await O.close();

ok(errors.length === 0, `no page errors or policy refusals in the page (${errors.slice(0, 3).join(' | ')})`);
await browser.close(); await S.close();
console.log(fails ? `${fails} failed` : 'all ok');
process.exit(fails ? 1 : 0);
