// Hindenburg — Vox-style explainer, 1080x1920, stepped on twos (12 poses/s).
// Every frame is a pure function of time: window.seek(seconds).
(function () {
  const W = 1080, H = 1920, POSES = 12;
  const C = { red: '#B8312A', cream: '#F1E6D0', paper: '#FBF7EE', navy: '#14213D', yellow: '#F2C230', ink: '#0B1426' };

  // Shot start times (seconds). Adjusted to the voice track by timings.json if present.
  const SHOTS = window.SHOT_TIMES || [0, 3.5, 7.5, 12, 16, 20.5, 25.5, 32, 37.5, 40.5, 45, 48, 52];
  const DURATION = SHOTS[SHOTS.length - 1];

  const cv = document.getElementById('c');
  cv.width = W; cv.height = H;
  let ctx = cv.getContext('2d');

  // ---------- helpers ----------
  function rng(seed) { let a = seed >>> 0; return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
  const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);
  const prog = (t, s, d) => easeOut((t - s) / d);
  const lin = (t, s, d) => clamp((t - s) / d);

  function tornPath(x, y, w, h, seed, jag = 10, step = 22) {
    const r = rng(seed); ctx.beginPath();
    let first = true;
    const pt = (px, py) => { if (first) { ctx.moveTo(px, py); first = false; } else ctx.lineTo(px, py); };
    for (let i = 0; i <= w; i += step) pt(x + i, y + (r() - 0.5) * jag);
    for (let i = 0; i <= h; i += step) pt(x + w + (r() - 0.5) * jag * 0.6, y + i);
    for (let i = w; i >= 0; i -= step) pt(x + i, y + h + (r() - 0.5) * jag);
    for (let i = h; i >= 0; i -= step) pt(x + (r() - 0.5) * jag * 0.6, y + i);
    ctx.closePath();
  }
  function card(x, y, w, h, color, seed, rot = 0, jag = 10) {
    ctx.save();
    ctx.translate(x + w / 2, y + h / 2); ctx.rotate(rot); ctx.translate(-w / 2, -h / 2);
    ctx.shadowColor = 'rgba(11,20,38,0.35)'; ctx.shadowBlur = 18; ctx.shadowOffsetX = 6; ctx.shadowOffsetY = 10;
    ctx.fillStyle = color; tornPath(0, 0, w, h, seed, jag); ctx.fill();
    ctx.shadowColor = 'transparent';
    ctx.globalAlpha = 0.18; ctx.drawImage(grainTile, 0, 0, w, h, 0, 0, w, h); ctx.globalAlpha = 1;
    ctx.restore();
  }
  function text(str, x, y, size, color, font = 'Anton', align = 'center', maxW = 960) {
    let s = size;
    ctx.font = `${s}px ${font}`;
    while (ctx.measureText(str).width > maxW && s > 20) { s -= 4; ctx.font = `${s}px ${font}`; }
    ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'middle';
    ctx.fillText(str, x, y);
    return s;
  }
  // Card that drops in (stepped by the global quantiser).
  function dropCard(t, start, x, y, w, h, color, seed, rot) {
    const p = prog(t, start, 0.35);
    if (p <= 0) return false;
    ctx.save(); ctx.globalAlpha = clamp(p * 2);
    card(x, y - (1 - p) * 90, w, h, color, seed, rot * p + (1 - p) * rot * 3);
    ctx.restore();
    return true;
  }
  function slamText(t, start, str, x, y, size, color, font) {
    const p = prog(t, start, 0.25);
    if (p <= 0) return;
    ctx.save(); ctx.translate(x, y); const s = 1.35 - 0.35 * p; ctx.scale(s, s);
    ctx.globalAlpha = clamp(p * 1.5); text(str, 0, 0, size, color, font); ctx.restore();
  }
  function bg(color) { ctx.fillStyle = color; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = color === C.navy ? 0.10 : 0.22; ctx.drawImage(paperTex, 0, 0); ctx.globalAlpha = 1; }

  // Airship silhouette, centred at (0,0), length L.
  function ship(L, color, flame = 0, t = 0) {
    const h = L * 0.17;
    ctx.save();
    ctx.fillStyle = color;
    // fins
    ctx.beginPath();
    ctx.moveTo(-L * 0.36, 0); ctx.lineTo(-L * 0.5, -h * 0.95); ctx.lineTo(-L * 0.47, 0); ctx.lineTo(-L * 0.5, h * 0.95); ctx.closePath(); ctx.fill();
    // hull
    ctx.beginPath(); ctx.ellipse(0, 0, L * 0.5, h / 2, 0, 0, Math.PI * 2); ctx.fill();
    // gondola
    ctx.fillRect(L * 0.18, h * 0.42, L * 0.08, h * 0.16);
    // ribs
    ctx.strokeStyle = 'rgba(0,0,0,0.18)'; ctx.lineWidth = 3;
    for (let i = -4; i <= 4; i++) { const x = i * L * 0.1; const yy = Math.sqrt(Math.max(0, 1 - (x / (L * 0.5)) ** 2)) * h / 2; ctx.beginPath(); ctx.moveTo(x, -yy); ctx.lineTo(x, yy); ctx.stroke(); }
    ctx.restore();
    if (flame > 0) flames(-L * 0.5, L * (0.25 + 0.75 * flame), h, t, L);
  }
  function flames(x0, len, h, t, L) {
    const frame = Math.floor(t * POSES);
    const r = rng(1000 + frame);
    for (let i = 0; i < 26; i++) {
      const fx = x0 + r() * len, fy = (r() - 0.6) * h * 0.9;
      const s = (0.35 + r() * 0.65) * h * 0.8;
      ctx.fillStyle = r() > 0.45 ? C.red : C.yellow;
      ctx.beginPath(); ctx.moveTo(fx - s * 0.4, fy + s * 0.3);
      ctx.quadraticCurveTo(fx, fy - s * 1.6, fx + s * 0.4, fy + s * 0.3); ctx.closePath(); ctx.fill();
    }
  }
  function markerCircle(cx, cy, rx, ry, p, color) {
    if (p <= 0) return;
    ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = 12; ctx.lineCap = 'round';
    ctx.beginPath();
    const r = rng(77); const steps = Math.floor(60 * p);
    for (let i = 0; i <= steps; i++) {
      const a = -Math.PI / 2 + (i / 60) * Math.PI * 2.15;
      const j = 1 + (r() - 0.5) * 0.04;
      const px = cx + Math.cos(a) * rx * j, py = cy + Math.sin(a) * ry * j;
      i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
    }
    ctx.stroke(); ctx.restore();
  }
  const stampCv = document.createElement('canvas'); stampCv.width = W; stampCv.height = H;
  function stamp(t, start, lines, x, y, rot, color, size = 120) {
    const p = prog(t, start, 0.2);
    if (p <= 0) return;
    const main = ctx; ctx = stampCv.getContext('2d'); ctx.clearRect(0, 0, W, H);
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); const s = 1.6 - 0.6 * p; ctx.scale(s, s); ctx.globalAlpha = clamp(p * 1.4);
    const lh = size * 1.05, bh = lh * lines.length + 60;
    ctx.font = `${size}px Anton`;
    const bw = Math.max(...lines.map(l => ctx.measureText(l).width)) + 90;
    ctx.strokeStyle = color; ctx.lineWidth = 14; ctx.strokeRect(-bw / 2, -bh / 2, bw, bh);
    ctx.lineWidth = 5; ctx.strokeRect(-bw / 2 + 18, -bh / 2 + 18, bw - 36, bh - 36);
    lines.forEach((l, i) => text(l, 0, -bh / 2 + 30 + lh * (i + 0.5), size, color));
    // ink wear
    ctx.globalCompositeOperation = 'destination-out'; const r = rng(55);
    for (let i = 0; i < 140; i++) { ctx.beginPath(); ctx.arc((r() - 0.5) * bw, (r() - 0.5) * bh, r() * 7, 0, 7); ctx.fill(); }
    ctx.restore();
    ctx = main; ctx.drawImage(stampCv, 0, 0);
  }
  function chip(str, x, y, color, txtColor, size = 54, seed = 9, rot = 0) {
    ctx.font = `${size}px Oswald`;
    const w = ctx.measureText(str).width + 70, h = size * 1.6;
    card(x - w / 2, y - h / 2, w, h, color, seed, rot, 6);
    ctx.save(); ctx.translate(x, y); ctx.rotate(rot); text(str, 0, 2, size, txtColor, 'Oswald'); ctx.restore();
  }

  // ---------- textures (built once, seeded) ----------
  function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
  const paperTex = makeCanvas(W, H);
  (() => { const g = paperTex.getContext('2d'); const id = g.createImageData(W, H); const r = rng(3);
    for (let i = 0; i < id.data.length; i += 4) { const v = 128 + (r() - 0.5) * 90; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; }
    g.putImageData(id, 0, 0); g.globalCompositeOperation = 'overlay'; g.globalAlpha = 0.5;
    for (let i = 0; i < 600; i++) { g.strokeStyle = r() > 0.5 ? '#000' : '#fff'; g.lineWidth = r() * 2; g.beginPath(); const x = r() * W, y = r() * H; g.moveTo(x, y); g.lineTo(x + (r() - 0.5) * 120, y + (r() - 0.5) * 40); g.stroke(); } })();
  const grainTile = makeCanvas(W, H);
  (() => { const g = grainTile.getContext('2d'); const id = g.createImageData(W, H); const r = rng(8);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; } g.putImageData(id, 0, 0); })();
  const filmGrain = [0, 1, 2, 3].map(k => { const c = makeCanvas(540, 960); const g = c.getContext('2d'); const id = g.createImageData(540, 960); const r = rng(100 + k);
    for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; } g.putImageData(id, 0, 0); return c; });
  const halftone = makeCanvas(W, H);
  (() => { const g = halftone.getContext('2d'); g.fillStyle = '#000';
    for (let y = 0; y < H; y += 14) for (let x = (y / 14) % 2 ? 7 : 0; x < W; x += 14) { const d = Math.hypot(x - W / 2, y - H / 2) / Math.hypot(W / 2, H / 2); g.beginPath(); g.arc(x, y, 1 + d * 3.2, 0, 7); g.fill(); } })();
  const vignette = makeCanvas(W, H);
  (() => { const g = vignette.getContext('2d'); const gr = g.createRadialGradient(W / 2, H / 2, H * 0.3, W / 2, H / 2, H * 0.72); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,0.55)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); })();
  const edgeMask = makeCanvas(W, H);
  (() => { const g = edgeMask.getContext('2d'); const gr = g.createRadialGradient(W / 2, H / 2, H * 0.36, W / 2, H / 2, H * 0.62); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,1)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); })();
  const fx = makeCanvas(W, H), fxc = fx.getContext('2d');

  function post(t) {
    // halftone + grain + vignette
    ctx.globalCompositeOperation = 'multiply'; ctx.globalAlpha = 0.10; ctx.drawImage(halftone, 0, 0);
    ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = 0.16; ctx.drawImage(filmGrain[Math.floor(t * POSES) % 4], 0, 0, W, H);
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1; ctx.drawImage(vignette, 0, 0);
    // colour fringing at the edges only
    [[1.010, '#ff2a2a'], [0.990, '#2a6bff']].forEach(([s, col]) => {
      fxc.globalCompositeOperation = 'source-over'; fxc.clearRect(0, 0, W, H);
      fxc.drawImage(cv, W * (1 - s) / 2, H * (1 - s) / 2, W * s, H * s);
      fxc.globalCompositeOperation = 'multiply'; fxc.fillStyle = col; fxc.fillRect(0, 0, W, H);
      fxc.globalCompositeOperation = 'destination-in'; fxc.drawImage(edgeMask, 0, 0);
      ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = 0.22; ctx.drawImage(fx, 0, 0);
    });
    ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  }

  // ---------- shots ----------
  const shots = [
    // 1 — the question
    (t, d) => {
      bg(C.navy);
      ctx.save(); ctx.translate(540, 470 + Math.sin(t * 2) * 6); ctx.rotate(-0.05); ship(820, C.cream, 0.35 + lin(t, 0, d) * 0.4, t); ctx.restore();
      const p = prog(t, 0, 0.3);
      if (p > 0) { ctx.save(); ctx.translate(-(1 - p) * 1100, 0); card(40, 820, 1000, 640, C.red, 11, -0.02, 14); ctx.restore(); }
      slamText(t, 0.15, '¿POR QUÉ', 540, 940, 190, C.cream);
      slamText(t, 0.45, 'CAYÓ EL', 540, 1130, 190, C.cream);
      slamText(t, 0.75, 'HINDENBURG?', 540, 1330, 190, C.yellow);
    },
    // 2 — date and place
    (t, d) => {
      bg(C.paper);
      if (dropCard(t, 0, 110, 380, 860, 300, C.navy, 21, -0.03)) text('6 DE MAYO', 540, 530 - (1 - prog(t, 0, .35)) * 90, 170, C.cream);
      if (dropCard(t, 0.4, 150, 720, 780, 400, C.red, 22, 0.02)) text('1937', 540, 925 - (1 - prog(t, .4, .35)) * 90, 330, C.cream);
      if (prog(t, 1.0, 0.3) > 0) chip('LAKEHURST, NUEVA JERSEY', 540, 1250, C.yellow, C.navy, 64, 23, -0.02);
    },
    // 3 — 245 m, 97 aboard
    (t, d) => {
      bg(C.cream);
      const p = prog(t, 0, 0.5);
      ctx.save(); ctx.translate(540 + (1 - p) * 900, 560); ship(940, C.navy); ctx.restore();
      const m = prog(t, 0.6, 0.6);
      if (m > 0) { ctx.strokeStyle = C.red; ctx.lineWidth = 8; const x1 = 70, x2 = 70 + 940 * m; ctx.beginPath(); ctx.moveTo(x1, 760); ctx.lineTo(x2, 760); ctx.moveTo(x1, 735); ctx.lineTo(x1, 785); if (m > 0.98) { ctx.moveTo(1010, 735); ctx.lineTo(1010, 785); } ctx.stroke(); }
      if (m > 0.9) chip('245 METROS', 540, 850, C.red, C.cream, 70, 31);
      if (dropCard(t, 1.4, 200, 1020, 680, 420, C.navy, 32, -0.015)) {
        const n = Math.round(97 * lin(t, 1.6, 1.2));
        text(String(n), 540, 1190, 260, C.yellow);
        text('PERSONAS A BORDO', 540, 1360, 64, C.cream, 'Oswald');
      }
    },
    // 4 — 34 seconds
    (t, d) => {
      bg(C.navy);
      const f = lin(t, 0.3, 2.6);
      ctx.save(); ctx.translate(540, 560 + f * 260); ctx.rotate(-0.04 - f * 0.32); ship(860, C.cream, f, t); ctx.restore();
      if (dropCard(t, 0.1, 190, 1080, 700, 360, C.red, 41, 0.02)) {
        const s = Math.min(34, Math.floor(34 * lin(t, 0.3, 2.6)));
        text('00:' + String(s).padStart(2, '0'), 540, 1265, 230, C.cream);
      }
      if (prog(t, 0.6, 0.3) > 0) chip('EN UNOS 34 SEGUNDOS', 540, 1520, C.yellow, C.navy, 60, 42, -0.02);
    },
    // 5 — 36 died, 62 survived (98 = 97 aboard + 1 on the ground)
    (t, d) => {
      bg(C.paper);
      const cols = 7, rows = 14, tw = 92, th = 62, gx = 18, gy = 14;
      const gw = cols * tw + (cols - 1) * gx, x0 = (W - gw) / 2, y0 = 330;
      for (let i = 0; i < 98; i++) {
        const c = i % cols, r = Math.floor(i / cols);
        const appear = lin(t, r * 0.05, 0.1);
        if (appear <= 0) continue;
        const dead = i < 36 && t > 1.1 + i * 0.025;
        card(x0 + c * (tw + gx), y0 + r * (th + gy), tw, th, dead ? C.red : C.navy, 500 + i, 0, 5);
      }
      if (prog(t, 1.4, .3) > 0) chip('36 MURIERON', 300, 1450, C.red, C.cream, 62, 51, -0.02);
      if (prog(t, 2.2, .3) > 0) chip('62 SOBREVIVIERON', 760, 1450, C.navy, C.cream, 62, 52, 0.02);
      if (prog(t, 2.6, .3) > 0) text('35 A BORDO + 1 EN TIERRA', 540, 1570, 40, C.navy, 'Oswald');
    },
    // 6 — helium vs hydrogen
    (t, d) => {
      bg(C.cream);
      const tile = (x, sym, name, num, col, start, seed) => {
        if (!dropCard(t, start, x, 520, 420, 520, col, seed, 0)) return;
        const o = (1 - prog(t, start, .35)) * 90;
        text(num, x + 60, 590 - o, 54, C.cream, 'Oswald', 'left');
        text(sym, x + 210, 780 - o, 260, C.cream);
        text(name, x + 210, 970 - o, 64, C.cream, 'Oswald');
      };
      tile(90, 'He', 'HELIO', '2', C.navy, 0, 61);
      tile(570, 'H', 'HIDRÓGENO', '1', C.red, 1.3, 62);
      const x = prog(t, 0.9, 0.35);
      if (x > 0) { ctx.strokeStyle = C.yellow; ctx.lineWidth = 22; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(120, 560); ctx.lineTo(120 + 360 * x, 560 + 440 * x); ctx.stroke();
        if (x > .99) { const y = prog(t, 1.1, .3); ctx.beginPath(); ctx.moveTo(480, 560); ctx.lineTo(480 - 360 * y, 560 + 440 * y); ctx.stroke(); } }
      if (t > 1.9) { ctx.save(); ctx.translate(780, 1140); flames(-150, 300, 150, t, 300); ctx.restore(); }
      if (prog(t, 2.2, .3) > 0) chip('UN GAS QUE ARDE', 540, 1330, C.yellow, C.navy, 72, 63, -0.02);
      if (prog(t, 0.4, .3) > 0) text('NO TENÍA HELIO', 540, 380, 120, C.navy);
    },
    // 7 — the 1927 law
    (t, d) => {
      bg(C.paper);
      if (prog(t, 0, .3) > 0) chip('EL HELIO SALÍA CASI TODO DE EE.UU.', 540, 330, C.navy, C.cream, 52, 71, -0.015);
      if (dropCard(t, 0.6, 150, 480, 780, 960, C.cream, 72, 0.015)) {
        const o = (1 - prog(t, .6, .35)) * 90;
        ctx.save(); ctx.translate(540, 960 - o); ctx.rotate(0.015);
        text('LEY DE CONTROL', 0, -380, 84, C.navy); text('DEL HELIO', 0, -290, 84, C.navy);
        text('ENMIENDA DE 1927', 0, -200, 52, C.red, 'Oswald');
        const r = rng(73); ctx.fillStyle = 'rgba(20,33,61,0.35)';
        for (let i = 0; i < 9; i++) ctx.fillRect(-300, -120 + i * 44, 600 * (0.6 + r() * 0.4), 14);
        ctx.restore();
      }
      stamp(t, 2.4, ['NO EXPORTAR', 'SIN PERMISO', 'DEL PRESIDENTE'], 540, 1240, -0.12, C.red, 82);
    },
    // 8 — late, through a storm
    (t, d) => {
      bg(C.navy);
      const frame = Math.floor(t * POSES), r = rng(800 + Math.floor(frame / 3));
      if (r() > 0.55) { ctx.fillStyle = 'rgba(242,194,48,0.10)'; ctx.fillRect(0, 0, W, H); }
      for (let k = 0; k < 2; k++) if (r() > 0.4 || (k === 0 && frame % 6 < 2)) { ctx.strokeStyle = C.yellow; ctx.lineWidth = 10; ctx.beginPath(); let x = 200 + r() * 680, y = 640; ctx.moveTo(x, y); for (let i = 0; i < 6; i++) { x += (r() - 0.5) * 140; y += 70; ctx.lineTo(x, y); } ctx.stroke(); }
      ctx.save(); ctx.translate(-200 + lin(t, 0, d) * 1400, 860); ship(560, C.cream); ctx.restore();
      [[60, 300, 520, 200, 81], [520, 330, 520, 220, 82], [-40, 520, 460, 180, 83], [640, 560, 480, 170, 84]].forEach(([x, y, w, h, s], i) => {
        const p = prog(t, i * 0.12, .35); if (p <= 0) return; const rr = rng(s), yy = y - (1 - p) * 120;
        ctx.save(); ctx.shadowColor = 'rgba(0,0,0,0.4)'; ctx.shadowBlur = 20; ctx.shadowOffsetY = 10; ctx.fillStyle = '#34446A';
        ctx.beginPath(); for (let k = 0; k < 7; k++) { const cx = x + 60 + (k / 6) * (w - 120), rad = h * (0.32 + rr() * 0.3); ctx.moveTo(cx + rad, yy + h * 0.55); ctx.arc(cx, yy + h * 0.55 - rr() * h * 0.2, rad, 0, 7); }
        ctx.rect(x + 40, yy + h * 0.5, w - 80, h * 0.4); ctx.fill(); ctx.restore(); });
      if (prog(t, 0.5, .3) > 0) chip('+12 HORAS DE ATRASO', 540, 1180, C.yellow, C.navy, 70, 85, -0.02);
      if (prog(t, 2.2, .3) > 0) { card(110, 1320, 860, 250, C.red, 86, 0.015, 12); text('FRENTE DE TORMENTA', 540, 1400, 92, C.cream, 'Anton', 'center', 780); text('CARGADO DE ELECTRICIDAD', 540, 1500, 52, C.cream, 'Oswald'); }
    },
    // 9 — two investigations
    (t, d) => {
      bg(C.cream);
      if (prog(t, 0, .3) > 0) text('DOS INVESTIGACIONES', 540, 430, 110, C.navy);
      [[90, 'ALEMANIA', 91, 0.3], [570, 'EE.UU.', 92, 0.6]].forEach(([x, name, s, st]) => {
        if (dropCard(t, st, x, 600, 420, 520, C.navy, s, 0)) { const o = (1 - prog(t, st, .35)) * 90; text(name, x + 210, 800 - o, 96, C.cream, 'Anton', 'center', 360); text('INVESTIGACIÓN', x + 210, 920 - o, 46, C.yellow, 'Oswald'); }
      });
      if (prog(t, 1.4, .3) > 0) { card(150, 1250, 780, 200, C.red, 93, -0.015, 12); text('MISMA CONCLUSIÓN', 540, 1350, 96, C.cream); }
    },
    // 10 — static spark + leaking hydrogen
    (t, d) => {
      bg(C.navy);
      if (prog(t, 0, .3) > 0) text('LO MÁS PROBABLE:', 540, 380, 110, C.cream);
      ctx.save(); ctx.translate(560, 820); ship(960, C.cream); ctx.restore();
      // leaking hydrogen wisps near the tail
      const lk = lin(t, 0.4, 1.5); ctx.fillStyle = 'rgba(241,230,208,0.45)';
      for (let i = 0; i < 6; i++) { const yy = 720 - lk * (60 + i * 30); ctx.beginPath(); ctx.arc(250 + i * 22, yy, 10 + i * 3, 0, 7); ctx.fill(); }
      markerCircle(260, 760, 190, 120, prog(t, 1.2, 0.6), C.yellow);
      const frame = Math.floor(t * POSES);
      if (t > 1.6 && frame % 3 !== 0) { ctx.strokeStyle = C.yellow; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(250, 640); ctx.lineTo(225, 690); ctx.lineTo(262, 690); ctx.lineTo(236, 745); ctx.stroke(); }
      if (prog(t, 1.8, .3) > 0) chip('CHISPA DE ESTÁTICA', 540, 1130, C.yellow, C.navy, 70, 101, -0.02);
      if (prog(t, 2.6, .3) > 0) chip('+ HIDRÓGENO QUE SE ESCAPABA', 540, 1290, C.red, C.cream, 54, 102, 0.015);
    },
    // 11 — no direct proof
    (t, d) => {
      bg(C.paper);
      ctx.globalAlpha = 0.25; ctx.save(); ctx.translate(540, 700); ship(900, C.navy); ctx.restore(); ctx.globalAlpha = 1;
      if (prog(t, 0, .3) > 0) text('PERO…', 540, 420, 130, C.navy);
      stamp(t, 0.5, ['SIN PRUEBA', 'DIRECTA'], 540, 1080, -0.1, C.red, 150);
    },
    // 12 — takeaway
    (t, d) => {
      bg(C.red);
      const s = lin(t, 0, d);
      ctx.save(); ctx.translate(540, 560 + s * 140); ctx.rotate(-0.1 - s * 0.15); ship(760, C.navy, 0.3 + s * 0.7, t); ctx.restore();
      const p1 = prog(t, 0.1, .3); if (p1 > 0) { ctx.save(); ctx.translate(-(1 - p1) * 1100, 0); card(70, 960, 940, 260, C.navy, 121, -0.02, 14); ctx.restore(); }
      slamText(t, 0.2, 'UNA CHISPA.', 540, 1090, 170, C.cream);
      const p2 = prog(t, 1.1, .3); if (p2 > 0) { ctx.save(); ctx.translate((1 - p2) * 1100, 0); card(70, 1260, 940, 260, C.cream, 122, 0.02, 14); ctx.restore(); }
      slamText(t, 1.2, 'FIN DE UNA ERA.', 540, 1390, 160, C.navy);
    },
  ];

  function draw(time) {
    const t = Math.floor(clamp(time, 0, DURATION - 1e-6) * POSES) / POSES; // animate on twos
    let i = 0; while (i < shots.length - 1 && t >= SHOTS[i + 1]) i++;
    ctx.save(); ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
    shots[i](t - SHOTS[i], SHOTS[i + 1] - SHOTS[i]);
    ctx.restore();
    post(t);
  }
  window.DURATION = DURATION; window.POSES = POSES;
  window.seek = s => draw(s);
})();
