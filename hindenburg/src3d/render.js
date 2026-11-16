// Render hindenburg-3d.html to JPEG frames.
// Usage: node render.js <html> <outDir> [stills|from:to]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [, , html, out, mode] = process.argv;
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 540, height: 960 } });
  page.on('console', m => { if (m.type() === 'error') console.log('PAGE', m.text()); });
  page.on('pageerror', e => console.log('PAGEERR', e.message));
  await page.goto('file://' + path.resolve(html));
  await page.waitForFunction(() => window.ready === true, null, { timeout: 120000 });
  const { dur, fps, shots } = await page.evaluate(() => ({ dur: window.DURATION, fps: window.FPS, shots: window.SHOT_TIMES || [0, 3.5, 7.5, 12, 16, 20.5, 25.5, 32, 37.5, 40.5, 45, 48, 52] }));
  let frames;
  if (mode === 'stills') frames = shots.slice(0, -1).map((a, i) => a + (shots[i + 1] - a) * 0.6);
  else { let [a, b] = mode ? mode.split(':').map(Number) : [0, Math.ceil(dur * fps)]; frames = []; for (let i = a; i < Math.min(b, Math.ceil(dur * fps)); i++) frames.push(i); }
  const t0 = Date.now();
  for (let k = 0; k < frames.length; k++) {
    const f = frames[k]; const t = mode === 'stills' ? f : f / fps;
    const b64 = await page.evaluate(t => { window.seek(t); return document.getElementById('c').toDataURL('image/jpeg', 0.92).split(',')[1]; }, t);
    const name = mode === 'stills' ? String(k).padStart(5, '0') : String(f).padStart(5, '0');
    fs.writeFileSync(path.join(out, name + '.jpg'), Buffer.from(b64, 'base64'));
    if (k % 30 === 0) console.log(k, '/', frames.length, ((Date.now() - t0) / (k + 1) / 1000).toFixed(2) + 's/frame');
  }
  await browser.close();
})();
