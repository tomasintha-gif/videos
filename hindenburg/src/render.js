// Render index.html to JPEG frames at 12 poses/s (the film animates on twos).
// Usage: node render.js <index.html> <outDir> [onlyMidShotStills]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
(async () => {
  const [, , html, out, stills] = process.argv;
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  await page.goto('file://' + path.resolve(html));
  await page.waitForFunction(() => window.ready === true);
  const { dur, poses, shots } = await page.evaluate(() => ({ dur: window.DURATION, poses: window.POSES, shots: window.SHOT_TIMES || null }));
  let times;
  if (stills) {
    const s = shots || [0, 3.5, 7.5, 12, 16, 20.5, 25.5, 32, 37.5, 40.5, 45, 48, 52];
    times = s.slice(0, -1).map((a, i) => a + (s[i + 1] - a) * 0.75);
  } else times = Array.from({ length: Math.ceil(dur * poses) }, (_, i) => i / poses);
  for (let i = 0; i < times.length; i++) {
    const b64 = await page.evaluate(t => { window.seek(t); return document.getElementById('c').toDataURL('image/jpeg', 0.93).split(',')[1]; }, times[i]);
    fs.writeFileSync(path.join(out, String(i).padStart(5, '0') + '.jpg'), Buffer.from(b64, 'base64'));
    if (i % 60 === 0) console.log(i, '/', times.length);
  }
  await browser.close();
})();
