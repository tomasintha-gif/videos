// 2D cartoon characters drawn on canvas: big white head, marker outline,
// bean-shaped garment body, stick limbs. Identity comes from hat + clothes.
window.drawCharacter = function (opts) {
  const { hat = 'sailor', vest = '#1F3A68', scarf = '#C8322B', expr = 'neutral', arms = 'down', angry = false, prop = null, mustache = false, chain = false } = opts;
  const c = document.createElement('canvas'); c.width = 512; c.height = 800;
  const g = c.getContext('2d');
  g.lineCap = 'round'; g.lineJoin = 'round';
  let seed = 7;
  const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
  const wobble = (cx, cy, r, n = 40, j = 4) => { g.beginPath(); for (let i = 0; i <= n; i++) { const a = i / n * Math.PI * 2; const rr = r + (rnd() - 0.5) * j; i ? g.lineTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr) : g.moveTo(cx + Math.cos(a) * rr, cy + Math.sin(a) * rr); } g.closePath(); };

  // legs + feet
  g.strokeStyle = '#111'; g.lineWidth = 11;
  g.beginPath(); g.moveTo(228, 640); g.lineTo(214, 760); g.moveTo(286, 640); g.lineTo(300, 760); g.stroke();
  g.fillStyle = '#111'; g.beginPath(); g.ellipse(204, 764, 26, 12, 0, 0, 7); g.ellipse(312, 764, 26, 12, 0, 0, 7); g.fill();

  // arms (behind body for some poses)
  const armL = { down: [[176, 470], [128, 600]], up: [[176, 470], [86, 360]], point: [[176, 470], [120, 590]], hold: [[176, 470], [200, 560]], hips: [[176, 470], [120, 540]] }[arms];
  const armR = { down: [[336, 470], [384, 600]], up: [[336, 470], [426, 360]], point: [[336, 470], [470, 400]], hold: [[336, 470], [312, 560]], hips: [[336, 470], [392, 540]] }[arms];
  g.strokeStyle = '#111'; g.lineWidth = 10;
  [armL, armR].forEach(([a, b]) => { g.beginPath(); g.moveTo(...a); if (arms === 'hips') { g.lineTo(b[0], b[1]); g.lineTo(a[0] + (b[0] - a[0]) * 0.2, 590); } else g.lineTo(...b); g.stroke(); });
  g.fillStyle = '#111';
  [armL, armR].forEach(([, b]) => { if (arms !== 'hips') { g.beginPath(); g.arc(b[0], b[1], 9, 0, 7); g.fill(); } });

  // bean body = garment
  g.fillStyle = vest; g.strokeStyle = '#111'; g.lineWidth = 9;
  g.beginPath(); g.ellipse(256, 530, 98, 132, 0, 0, Math.PI * 2); g.fill(); g.stroke();
  // painted texture
  g.save(); g.clip(); g.globalAlpha = 0.18;
  for (let i = 0; i < 70; i++) { g.strokeStyle = rnd() > 0.5 ? '#fff' : '#000'; g.lineWidth = 2 + rnd() * 5; g.beginPath(); const x = 150 + rnd() * 210, y = 400 + rnd() * 260; g.moveTo(x, y); g.lineTo(x + 20 + rnd() * 30, y + (rnd() - 0.5) * 10); g.stroke(); }
  g.restore();
  // buttons + lapels
  g.fillStyle = '#111'; [500, 550, 600].forEach(y => { g.beginPath(); g.arc(256, y, 6, 0, 7); g.fill(); });
  if (chain) { g.strokeStyle = '#E8B730'; g.lineWidth = 6; g.beginPath(); g.moveTo(256, 550); g.quadraticCurveTo(300, 600, 330, 545); g.stroke(); }
  // scarf / tie
  if (scarf) { g.fillStyle = scarf; g.strokeStyle = '#111'; g.lineWidth = 5; g.beginPath(); g.moveTo(210, 412); g.lineTo(302, 412); g.lineTo(256, 470); g.closePath(); g.fill(); g.stroke(); }

  // head
  const hx = 256, hy = 250, hr = 160;
  g.fillStyle = angry ? '#7B3FB5' : '#FFFFFF';
  wobble(hx, hy, hr, 48, 5); g.fill();
  g.strokeStyle = '#111'; g.lineWidth = 13; wobble(hx, hy, hr, 48, 6); g.stroke();

  // face
  g.fillStyle = '#111'; g.strokeStyle = '#111';
  const brow = (x1, y1, x2, y2) => { g.lineWidth = 15; g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke(); };
  const dot = (x, y, r = 13) => { g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); };
  const bigEye = (x, y) => { g.fillStyle = '#fff'; g.lineWidth = 7; g.beginPath(); g.arc(x, y, 34, 0, 7); g.fill(); g.stroke(); g.fillStyle = '#111'; dot(x, y + 4, 14); };
  g.lineWidth = 9;
  if (expr === 'neutral') { brow(190, 205, 235, 210); brow(280, 210, 325, 205); dot(215, 250); dot(300, 250); g.lineWidth = 9; g.beginPath(); g.moveTo(225, 325); g.lineTo(290, 325); g.stroke(); }
  if (expr === 'smug') { brow(188, 215, 236, 205); brow(280, 200, 328, 212); g.lineWidth = 9; g.beginPath(); g.moveTo(198, 252); g.lineTo(232, 252); g.moveTo(284, 252); g.lineTo(318, 252); g.stroke(); g.beginPath(); g.moveTo(222, 322); g.quadraticCurveTo(270, 345, 300, 312); g.stroke(); }
  if (expr === 'surprised') { brow(185, 175, 232, 168); brow(282, 168, 330, 175); bigEye(212, 245); bigEye(302, 245); g.fillStyle = '#111'; g.beginPath(); g.ellipse(258, 335, 22, 30, 0, 0, 7); g.fill(); }
  if (expr === 'worried') { brow(190, 200, 235, 185); brow(282, 185, 326, 200); dot(215, 250); dot(300, 250); g.lineWidth = 9; g.beginPath(); g.moveTo(222, 335); g.quadraticCurveTo(258, 312, 296, 335); g.stroke(); }
  if (expr === 'sad') { brow(192, 205, 236, 192); brow(280, 192, 324, 205); dot(215, 255, 11); dot(300, 255, 11); g.lineWidth = 9; g.beginPath(); g.moveTo(225, 340); g.quadraticCurveTo(258, 318, 292, 340); g.stroke(); g.fillStyle = '#6BB7FF'; g.beginPath(); g.ellipse(316, 290, 9, 16, 0, 0, 7); g.fill(); }
  if (expr === 'angry') { brow(185, 195, 238, 228); brow(278, 228, 331, 195); dot(218, 258); dot(298, 258);
    g.fillStyle = '#fff'; g.lineWidth = 6; g.beginPath(); g.rect(205, 305, 106, 46); g.fill(); g.stroke(); g.beginPath(); for (let x = 226; x < 311; x += 21) { g.moveTo(x, 305); g.lineTo(x, 351); } g.moveTo(205, 328); g.lineTo(311, 328); g.stroke(); }
  if (expr === 'happy') { brow(192, 200, 236, 196); brow(280, 196, 324, 200); g.lineWidth = 9; g.beginPath(); g.arc(215, 258, 16, Math.PI, 0); g.arc(300, 258, 16, Math.PI, 0); g.stroke(); g.beginPath(); g.moveTo(215, 315); g.quadraticCurveTo(258, 360, 302, 315); g.stroke(); }
  if (mustache) { g.fillStyle = '#111'; g.beginPath(); g.ellipse(236, 300, 26, 10, 0.2, 0, 7); g.ellipse(280, 300, 26, 10, -0.2, 0, 7); g.fill(); }
  if (angry) { g.fillStyle = '#fff'; g.strokeStyle = '#111'; g.lineWidth = 5; [[70, 200], [52, 150], [442, 200], [460, 150]].forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 30, 0, 7); g.arc(x + 20, y - 20, 22, 0, 7); g.fill(); }); }

  // hats
  g.strokeStyle = '#111'; g.lineWidth = 9;
  if (hat === 'sailor') { // white navy cap
    g.fillStyle = '#F4F4F0'; g.beginPath(); g.moveTo(150, 140); g.quadraticCurveTo(256, 20, 362, 140); g.closePath(); g.fill(); g.stroke();
    g.beginPath(); g.ellipse(256, 142, 120, 28, 0, 0, 7); g.fill(); g.stroke(); g.fillStyle = '#1F3A68'; g.fillRect(170, 120, 172, 10); }
  if (hat === 'bowler') { g.fillStyle = '#1A1A1A'; g.beginPath(); g.arc(256, 130, 110, Math.PI, 0); g.fill(); g.beginPath(); g.ellipse(256, 132, 165, 30, 0, 0, 7); g.fill(); }
  if (hat === 'fedora') { g.fillStyle = '#6B4A2E'; g.beginPath(); g.ellipse(256, 132, 175, 32, 0, 0, 7); g.fill(); g.stroke(); g.beginPath(); g.moveTo(160, 132); g.lineTo(175, 40); g.quadraticCurveTo(256, 70, 337, 40); g.lineTo(352, 132); g.closePath(); g.fill(); g.stroke(); g.fillStyle = '#2B1C10'; g.fillRect(162, 102, 188, 22); }
  if (hat === 'peaked') { g.fillStyle = '#5E6670'; g.beginPath(); g.ellipse(256, 95, 160, 48, 0, 0, 7); g.fill(); g.stroke(); g.fillRect(168, 95, 176, 50); g.strokeRect(168, 95, 176, 50); g.fillStyle = '#111'; g.beginPath(); g.ellipse(256, 150, 120, 22, 0, 0, Math.PI); g.fill(); g.fillStyle = '#E8B730'; g.beginPath(); g.arc(256, 112, 12, 0, 7); g.fill(); }
  if (hat === 'captain') { g.fillStyle = '#F4F4F0'; g.beginPath(); g.ellipse(256, 95, 160, 48, 0, 0, 7); g.fill(); g.stroke(); g.fillStyle = '#1A2742'; g.fillRect(168, 95, 176, 50); g.fillStyle = '#111'; g.beginPath(); g.ellipse(256, 150, 120, 22, 0, 0, Math.PI); g.fill(); g.fillStyle = '#E8B730'; g.fillRect(200, 112, 112, 12); }

  // props in hand
  if (prop === 'watch') { const [x, y] = armR[1]; g.fillStyle = '#E8B730'; g.strokeStyle = '#111'; g.lineWidth = 6; g.beginPath(); g.arc(x, y - 20, 40, 0, 7); g.fill(); g.stroke(); g.fillStyle = '#fff'; g.beginPath(); g.arc(x, y - 20, 30, 0, 7); g.fill(); g.lineWidth = 5; g.beginPath(); g.moveTo(x, y - 20); g.lineTo(x, y - 42); g.moveTo(x, y - 20); g.lineTo(x + 16, y - 14); g.stroke(); }
  if (prop === 'magnifier') { const [x, y] = armR[1]; g.strokeStyle = '#111'; g.lineWidth = 10; g.beginPath(); g.moveTo(x, y); g.lineTo(x + 30, y - 50); g.stroke(); g.fillStyle = 'rgba(180,220,255,0.6)'; g.lineWidth = 8; g.beginPath(); g.arc(x + 50, y - 85, 42, 0, 7); g.fill(); g.stroke(); }
  return c;
};
