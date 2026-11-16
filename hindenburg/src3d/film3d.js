// Hindenburg — 3D stylised short (1080x1920, 30 fps). Pure function of time: window.seek(t).
(function () {
  const W = 1080, H = 1920, FPS = 30;
  const T = THREE;
  const SHOTS = window.SHOT_TIMES || [0, 3.5, 7.5, 12, 16, 20.5, 25.5, 32, 37.5, 40.5, 45, 48, 52];
  const DURATION = SHOTS[SHOTS.length - 1];
  const WORDS = window.WORD_TIMES || null; // [{w, s, e}]
  const SCRIPT = window.SCRIPT_LINES;

  // ---------- renderer + paint post-process ----------
  const glCanvas = document.createElement('canvas'); glCanvas.width = W; glCanvas.height = H;
  const renderer = new T.WebGLRenderer({ canvas: glCanvas, antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(W, H, false); renderer.setPixelRatio(1);
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFShadowMap;
  renderer.localClippingEnabled = true;
  renderer.outputColorSpace = T.SRGBColorSpace;
  const RW = 720, RH = 1280; const rt = new T.WebGLRenderTarget(RW, RH, { samples: 2 });
  rt.texture.colorSpace = T.SRGBColorSpace;
  const postScene = new T.Scene(), postCam = new T.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  const brushTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d'); g.fillStyle = '#808080'; g.fillRect(0, 0, 512, 512); let s = 3; const r = () => (s = (s * 16807) % 2147483647) / 2147483647;
    for (let i = 0; i < 2500; i++) { const v = 100 + r() * 56; g.strokeStyle = `rgb(${v},${v},${v})`; g.lineWidth = 2 + r() * 6; const x = r() * 512, y = r() * 512, a = r() * 0.6 - 0.3; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.cos(a) * 30, y + Math.sin(a) * 30); g.stroke(); }
    const t = new T.CanvasTexture(c); t.wrapS = t.wrapT = T.RepeatWrapping; return t; })();
  const postMat = new T.ShaderMaterial({
    uniforms: { tDiffuse: { value: rt.texture }, tBrush: { value: brushTex }, res: { value: new T.Vector2(RW, RH) } },
    vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `
      uniform sampler2D tDiffuse, tBrush; uniform vec2 res; varying vec2 vUv;
      vec3 sat(vec3 c, float s){ float l = dot(c, vec3(0.299,0.587,0.114)); return mix(vec3(l), c, s); }
      void main(){
        vec2 px = 0.75 / res;
        // Kuwahara (radius 2): painterly flattening
        vec3 m[4]; vec3 s2[4];
        for (int k=0;k<4;k++){ m[k]=vec3(0.0); s2[k]=vec3(0.0); }
        for (int j=-2;j<=0;j++) for (int i=-2;i<=0;i++){
          vec3 a = texture2D(tDiffuse, vUv + vec2(float(i),float(j))*px*1.5).rgb; m[0]+=a; s2[0]+=a*a;
          vec3 b = texture2D(tDiffuse, vUv + vec2(float(-i),float(j))*px*1.5).rgb; m[1]+=b; s2[1]+=b*b;
          vec3 c = texture2D(tDiffuse, vUv + vec2(float(i),float(-j))*px*1.5).rgb; m[2]+=c; s2[2]+=c*c;
          vec3 d = texture2D(tDiffuse, vUv + vec2(float(-i),float(-j))*px*1.5).rgb; m[3]+=d; s2[3]+=d*d;
        }
        vec3 best = vec3(0.0); float bv = 1e9;
        for (int k=0;k<4;k++){ vec3 mu = m[k]/9.0; vec3 v = abs(s2[k]/9.0 - mu*mu); float sv = v.r+v.g+v.b; if (sv < bv){ bv = sv; best = mu; } }
        vec3 col = sat(best, 1.28);
        float br = texture2D(tBrush, vUv * vec2(2.2, 3.9)).r - 0.5;
        col += br * 0.10;
        col = floor(col * 9.0 + 0.5) / 9.0 * 0.6 + col * 0.4; // soft posterise bands
        float v = smoothstep(1.15, 0.35, length((vUv - 0.5) * vec2(1.0, 1.4)));
        col *= mix(0.78, 1.0, v);
        gl_FragColor = vec4(col, 1.0);
      }`,
    depthTest: false, depthWrite: false,
  });
  postScene.add(new T.Mesh(new T.PlaneGeometry(2, 2), postMat));

  // ---------- material + texture helpers ----------
  const gradMap = (() => { const d = new Uint8Array([70, 70, 70, 255, 160, 160, 160, 255, 255, 255, 255, 255]); const t = new T.DataTexture(d, 3, 1, T.RGBAFormat); t.minFilter = t.magFilter = T.NearestFilter; t.needsUpdate = true; return t; })();
  const toon = (color, map) => new T.MeshToonMaterial({ color, gradientMap: gradMap, map: map || null });
  function canvasTex(w, h, fn, repeat) { const c = document.createElement('canvas'); c.width = w; c.height = h; fn(c.getContext('2d'), w, h); const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; t.anisotropy = 4; if (repeat) { t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); } return t; }
  let sd = 11; const rnd = () => (sd = (sd * 16807) % 2147483647) / 2147483647;
  const strokes = (g, w, h, n, cols, len = 40, lw = 6) => { for (let i = 0; i < n; i++) { g.strokeStyle = cols[Math.floor(rnd() * cols.length)]; g.lineWidth = lw * (0.5 + rnd()); const x = rnd() * w, y = rnd() * h; g.beginPath(); g.moveTo(x, y); g.lineTo(x + len * (0.5 + rnd()), y + (rnd() - 0.5) * 8); g.stroke(); } };
  const grassTex = canvasTex(512, 512, (g, w, h) => { g.fillStyle = '#7FA04A'; g.fillRect(0, 0, w, h); strokes(g, w, h, 900, ['#6E9140', '#93B356', '#A6A85A', '#5F7F38'], 30, 7); }, [400, 400]);
  const sandTex = canvasTex(512, 512, (g, w, h) => { g.fillStyle = '#D9B47A'; g.fillRect(0, 0, w, h); strokes(g, w, h, 900, ['#C99E62', '#E6C38C', '#B98C55'], 26, 6); }, [70, 70]);
  const woodTex = canvasTex(256, 256, (g, w, h) => { g.fillStyle = '#8E4A2B'; g.fillRect(0, 0, w, h); strokes(g, w, h, 300, ['#7A3D22', '#A35A35', '#6B331C'], 80, 4); }, [2, 2]);
  const hullTex = canvasTex(1024, 256, (g, w, h) => { g.fillStyle = '#C9CCD0'; g.fillRect(0, 0, w, h); strokes(g, w, h, 700, ['#B7BBC1', '#DADDE0', '#AEB2B8'], 50, 6);
    g.strokeStyle = 'rgba(70,75,85,0.55)'; g.lineWidth = 3; for (let x = 0; x < w; x += 32) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke(); } for (let y = 0; y < h; y += 22) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); } });
  function labelTex(lines, opts = {}) {
    const { w = 1024, h = 512, bg = '#F3E7C9', fg = '#1B1B1B', font = 'Anton', border = '#5A3A22', sizes } = opts;
    return canvasTex(w, h, (g) => { g.fillStyle = bg; g.fillRect(0, 0, w, h); strokes(g, w, h, 160, ['rgba(0,0,0,0.06)', 'rgba(255,255,255,0.12)'], 60, 8);
      if (border) { g.strokeStyle = border; g.lineWidth = 24; g.strokeRect(12, 12, w - 24, h - 24); }
      g.fillStyle = fg; g.textAlign = 'center'; g.textBaseline = 'middle';
      const n = lines.length; lines.forEach((l, i) => { let s = (sizes && sizes[i]) || h / (n + 0.8); g.font = `${s}px ${font}`; while (g.measureText(l).width > w * 0.88) { s -= 4; g.font = `${s}px ${font}`; } g.fillText(l, w / 2, h * (i + 0.5 + 0.2) / (n + 0.4)); }); });
  }
  function sign(lines, w, h, opts) { const m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ map: labelTex(lines, opts), side: T.DoubleSide })); return m; }

  function makeSky(scene, top = '#1D4FB8', bottom = '#9CC7F2') {
    const g = new T.SphereGeometry(4000, 32, 16);
    const m = new T.ShaderMaterial({ side: T.BackSide, depthWrite: false, uniforms: { top: { value: new T.Color(top) }, bot: { value: new T.Color(bottom) } },
      vertexShader: 'varying vec3 p; void main(){ p = normalize(position); gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 top, bot; varying vec3 p; void main(){ float k = smoothstep(-0.05, 0.6, p.y); gl_FragColor = vec4(mix(bot, top, k), 1.0); }' });
    const sky = new T.Mesh(g, m); scene.add(sky); return sky;
  }
  const cloudTex = canvasTex(512, 256, (g, w, h) => { for (let i = 0; i < 26; i++) { const x = 60 + rnd() * 390, y = 80 + rnd() * 110, rx = 50 + rnd() * 90, ry = 14 + rnd() * 22; g.fillStyle = `rgba(255,255,255,${0.55 + rnd() * 0.4})`; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, 7); g.fill(); } });
  function clouds(scene, n, y0, spread, tint = 0xffffff, seed = 1) { sd = seed * 977 + 13; for (let i = 0; i < n; i++) { const s = new T.Sprite(new T.SpriteMaterial({ map: cloudTex, color: tint, depthWrite: false, fog: false })); const a = rnd() * Math.PI * 2, r = spread * (0.4 + rnd() * 0.6); s.position.set(Math.cos(a) * r, y0 + rnd() * 400, Math.sin(a) * r); const k = 500 + rnd() * 700; s.scale.set(k, k / 2, 1); scene.add(s); } }
  function lights(scene, sunPos = [300, 500, 200], sky = 0xBFD8FF, ground = 0x8A6A4A, sunCol = 0xFFF1D6, range = 420) {
    scene.add(new T.HemisphereLight(sky, ground, 1.25));
    const d = new T.DirectionalLight(sunCol, 2.6); d.position.set(...sunPos); d.castShadow = true;
    d.shadow.mapSize.set(1536, 1536); const sc = d.shadow.camera; sc.left = -range; sc.right = range; sc.top = range; sc.bottom = -range; sc.near = 1; sc.far = 3000; d.shadow.bias = -0.0008;
    scene.add(d); scene.add(d.target); return d;
  }

  // ---------- characters ----------
  const charCache = new Map();
  function charTex(key, opts) { if (!charCache.has(key)) { const t = new T.CanvasTexture(window.drawCharacter(opts)); t.colorSpace = T.SRGBColorSpace; charCache.set(key, t); } return charCache.get(key); }
  const CAST = {
    sailor: { hat: 'sailor', vest: '#1F3A68', scarf: '#C8322B' },
    passenger: { hat: 'fedora', vest: '#C9A227', scarf: '#7A1F1F', chain: true },
    official: { hat: 'bowler', vest: '#C9A227', scarf: '#2B2B2B', chain: true, mustache: true },
    german: { hat: 'peaked', vest: '#5E6670', scarf: '#1B1B1B' },
    american: { hat: 'fedora', vest: '#7A5230', scarf: '#1F3A68' },
    captain: { hat: 'captain', vest: '#1A2742', scarf: '#E8B730', mustache: true },
  };
  function actor(scene, who, height = 2) {
    const mat = new T.SpriteMaterial({ map: charTex(who + 'neutraldown', { ...CAST[who] }), transparent: true });
    const s = new T.Sprite(mat); s.center.set(0.5, 0); s.scale.set(height * 0.64, height, 1);
    const shadow = new T.Mesh(new T.CircleGeometry(height * 0.22, 24), new T.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.28, depthWrite: false }));
    shadow.rotation.x = -Math.PI / 2;
    const grp = new T.Group(); grp.add(s); grp.add(shadow); shadow.position.y = 0.02; scene.add(grp);
    return { grp, s, set(expr = 'neutral', arms = 'down', extra = {}) { const o = { ...CAST[who], expr, arms, ...extra }; mat.map = charTex(who + expr + arms + JSON.stringify(extra), o); },
      bob(t, amt = 0.04) { s.position.y = Math.abs(Math.sin(t * 5)) * amt * s.scale.y; s.material.rotation = Math.sin(t * 2.3) * 0.04; } };
  }

  // ---------- the airship ----------
  const L = 245, R = 20.5;
  function makeShip() {
    const grp = new T.Group();
    const pts = []; for (let i = 0; i <= 60; i++) { const s = i / 60; const r = R * Math.pow(Math.max(0, Math.sin(Math.PI * Math.pow(s, 0.85))), 0.55); pts.push(new T.Vector2(Math.max(r, 0.01), s * L - L / 2)); }
    const geo = new T.LatheGeometry(pts, 48);
    const clip = new T.Plane(new T.Vector3(-1, 0, 0), 1e5);
    const hullMat = toon(0xffffff, hullTex); hullMat.clippingPlanes = [clip]; hullMat.side = T.DoubleSide;
    const hull = new T.Mesh(geo, hullMat); hull.rotation.z = Math.PI / 2; hull.castShadow = true; grp.add(hull); // +y -> -x : s=0 (fat) at +x? see below
    hull.rotation.z = -Math.PI / 2; // lathe +y -> world +x ; fat end (s≈0.44) toward -x = nose
    const skel = new T.Mesh(new T.LatheGeometry(pts, 14), new T.MeshBasicMaterial({ color: 0x2A1A12, wireframe: true }));
    skel.rotation.z = -Math.PI / 2; skel.visible = false; grp.add(skel);
    // fins at tail (+x)
    const finMat = toon(0xC4C7CB, hullTex); finMat.clippingPlanes = [clip]; finMat.side = T.DoubleSide;
    for (let k = 0; k < 4; k++) { const sh = new T.Shape(); sh.moveTo(0, 0); sh.lineTo(-38, 0); sh.lineTo(-10, 17); sh.lineTo(0, 17); sh.closePath(); const f = new T.Mesh(new T.ExtrudeGeometry(sh, { depth: 0.8, bevelEnabled: false }), finMat); f.position.set(L / 2 - 10, 0, 0); const holder = new T.Group(); holder.rotation.x = k * Math.PI / 2; f.position.y = R * 0.32; holder.add(f); f.castShadow = true; grp.add(holder); }
    // control car + passenger windows
    const car = new T.Mesh(new T.BoxGeometry(14, 4, 4), toon(0xB8BCC2)); car.position.set(-L * 0.36, -R * 0.93, 0); car.castShadow = true; grp.add(car);
    const winMat = new T.MeshBasicMaterial({ color: 0xFFE7A0 });
    for (let i = 0; i < 16; i++) { const w = new T.Mesh(new T.BoxGeometry(2.2, 1.4, 0.3), winMat); w.position.set(-L * 0.24 + i * 3.1, -R * 0.62, R * 0.8); w.rotation.x = -0.6; grp.add(w); const w2 = w.clone(); w2.position.z *= -1; w2.rotation.x = 0.6; grp.add(w2); }
    // name decal
    const name = new T.Mesh(new T.PlaneGeometry(56, 8), new T.MeshBasicMaterial({ map: canvasTex(1024, 146, (g, w, h) => { g.clearRect(0, 0, w, h); g.fillStyle = '#B3261E'; g.font = '120px Anton'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('HINDENBURG', w / 2, h / 2 + 6); }), transparent: true }));
    name.position.set(-L * 0.3, 2, R * 0.99 + 0.3); grp.add(name);
    grp.userData = { clip, hull, skel, name, fins: grp.children.filter(c => c.isGroup) };
    return grp;
  }
  // Burn: progress 0..1 from tail (+x) to nose (-x).
  function setBurn(ship, p) {
    const { clip, skel, name } = ship.userData;
    ship.updateMatrixWorld(true);
    const cutLocal = new T.Vector3(L / 2 + 5 - p * (L + 10), 0, 0);
    const n = new T.Vector3(1, 0, 0).transformDirection(ship.matrixWorld).negate();
    clip.setFromNormalAndCoplanarPoint(n, cutLocal.clone().applyMatrix4(ship.matrixWorld));
    skel.visible = p > 0.001; name.visible = p < 0.88;
    return cutLocal.x;
  }
  const flameTex = [0, 1, 2].map(k => canvasTex(128, 192, (g) => { const grd = g.createRadialGradient(64, 130, 6, 64, 120, 70); grd.addColorStop(0, '#FFF6B0'); grd.addColorStop(0.35, '#FFC02E'); grd.addColorStop(0.7, '#F0561C'); grd.addColorStop(1, 'rgba(200,40,20,0)'); g.fillStyle = grd; g.beginPath(); g.moveTo(64, 4 + k * 10); g.bezierCurveTo(120, 80, 124, 170, 64, 186); g.bezierCurveTo(4, 170, 8, 80, 64, 4 + k * 10); g.fill(); }));
  const smokeTex = canvasTex(128, 128, (g) => { const grd = g.createRadialGradient(64, 64, 4, 64, 64, 62); grd.addColorStop(0, 'rgba(40,36,40,0.85)'); grd.addColorStop(1, 'rgba(40,36,40,0)'); g.fillStyle = grd; g.fillRect(0, 0, 128, 128); });
  function makeFire(scene, n = 90) { const arr = []; for (let i = 0; i < n; i++) { const s = new T.Sprite(new T.SpriteMaterial({ map: flameTex[i % 3], transparent: true, depthWrite: false })); s.center.set(0.5, 0.1); s.visible = false; scene.add(s); arr.push(s); } const sm = []; for (let i = 0; i < 40; i++) { const s = new T.Sprite(new T.SpriteMaterial({ map: smokeTex, transparent: true, depthWrite: false })); s.visible = false; scene.add(s); sm.push(s); } return { arr, sm }; }
  // Place flames along the burnt part of the ship (local x from cut to tail).
  function updateFire(fire, ship, cutX, t, intensity = 1, onGround = false) {
    const pose = Math.floor(t * 12); let sdd = 1000 + pose; const r = () => (sdd = (sdd * 16807) % 2147483647) / 2147483647;
    ship.updateMatrixWorld(true);
    fire.arr.forEach((s, i) => { if (intensity <= 0) { s.visible = false; return; }
      const front = i < 30; const x = front ? cutX + (r() - 0.3) * 14 : cutX + r() * (L / 2 - cutX);
      if (x > L / 2) { s.visible = false; return; }
      const a = r() * Math.PI * 2, rad = R * (front ? 0.95 : 0.6) * r();
      const p = new T.Vector3(x, Math.sin(a) * rad, Math.cos(a) * rad).applyMatrix4(ship.matrixWorld);
      if (onGround) p.y = Math.max(p.y, 0);
      s.position.copy(p); const k = (front ? 26 : 16) * (0.6 + r() * 0.8) * intensity; s.scale.set(k * 0.66, k, 1); s.visible = true; });
    fire.sm.forEach((s, i) => { if (intensity <= 0) { s.visible = false; return; } const x = cutX + r() * (L / 2 - cutX); const p = new T.Vector3(x, 0, 0).applyMatrix4(ship.matrixWorld); const rise = ((t * 0.6 + i * 0.137) % 1); p.y += 20 + rise * 90; p.x += rise * 25; s.position.copy(p); const k = (30 + rise * 60) * intensity; s.scale.set(k, k, 1); s.material.opacity = (1 - rise) * 0.8; s.visible = true; });
  }

  // =========== SETS ===========
  // --- Lakehurst field (exterior) ---
  const field = new T.Scene(); field.fog = new T.Fog(0xA9CBEF, 900, 3600);
  makeSky(field); const fieldSun = lights(field, [260, 420, 300]); clouds(field, 26, 700, 2600, 0xffffff, 2);
  { const g = new T.Mesh(new T.PlaneGeometry(8000, 8000), toon(0xffffff, grassTex)); g.rotation.x = -Math.PI / 2; g.receiveShadow = true; field.add(g);
    const pad = new T.Mesh(new T.CircleGeometry(260, 64), toon(0xffffff, sandTex)); pad.rotation.x = -Math.PI / 2; pad.position.y = 0.05; pad.receiveShadow = true; field.add(pad); }
  // mooring mast (red/white lattice) at origin
  const mast = new T.Group(); field.add(mast);
  { const red = toon(0xC0392B), white = toon(0xF2EEE6); const h = 50;
    for (let i = 0; i < 4; i++) { const leg = new T.Mesh(new T.CylinderGeometry(0.5, 0.9, h, 6), i % 2 ? red : white); const a = i * Math.PI / 2 + Math.PI / 4; leg.position.set(Math.cos(a) * 4, h / 2, Math.sin(a) * 4); leg.castShadow = true; mast.add(leg); }
    for (let y = 4; y < h; y += 6) { const ring = new T.Mesh(new T.BoxGeometry(8.5, 0.6, 8.5), (y / 6) % 2 ? red : white); ring.position.y = y; ring.castShadow = true; mast.add(ring); }
    const top = new T.Mesh(new T.CylinderGeometry(2.5, 3.5, 5, 8), red); top.position.y = h + 2; top.castShadow = true; mast.add(top); }
  // hangar
  { const hang = new T.Mesh(new T.CylinderGeometry(55, 55, 320, 32, 1, false, 0, Math.PI), toon(0x9AA3AD)); hang.rotation.z = Math.PI / 2; hang.rotation.y = 0.3; hang.position.set(-520, 0, -620); hang.castShadow = hang.receiveShadow = true; field.add(hang);
    const door = new T.Mesh(new T.CircleGeometry(52, 32, 0, Math.PI), toon(0x30353C)); door.position.set(-520 + 160 * Math.cos(0.3), 0.1, -620 - 160 * Math.sin(0.3)); field.add(door); }
  // pines ring
  { const pine = toon(0x2F5A33), trunk = toon(0x5B3A22); sd = 77; for (let i = 0; i < 260; i++) { const a = rnd() * Math.PI * 2, r = 1150 + rnd() * 600; const h = 25 + rnd() * 30; const c = new T.Mesh(new T.ConeGeometry(h * 0.28, h, 6), pine); c.position.set(Math.cos(a) * r, h / 2 + 4, Math.sin(a) * r); field.add(c); const tr = new T.Mesh(new T.CylinderGeometry(1, 1.3, 6, 5), trunk); tr.position.set(c.position.x, 3, c.position.z); field.add(tr); } }
  // gate sign + calendar crate
  const gateSign = sign(['LAKEHURST', 'NUEVA JERSEY'], 16, 8, { bg: '#F3E7C9', fg: '#1F3A68', border: '#8E4A2B' }); gateSign.position.set(120, 9, 160); gateSign.rotation.y = 0.5; field.add(gateSign);
  { [-7, 7].forEach(dx => { const p = new T.Mesh(new T.BoxGeometry(0.8, 13, 0.8), toon(0xffffff, woodTex)); p.position.set(120 + dx * Math.cos(0.5), 6.5, 160 - dx * Math.sin(0.5)); p.castShadow = true; field.add(p); }); }
  const crate = new T.Mesh(new T.BoxGeometry(4.5, 3.4, 4.5), toon(0xffffff, woodTex)); crate.position.set(104, 1.7, 176); crate.castShadow = true; field.add(crate);
  const calendar = sign(['MAYO', '6', '1937'], 3.6, 4.8, { w: 512, h: 680, bg: '#FAF6EC', fg: '#B3261E', border: '#1B1B1B', sizes: [130, 300, 110] }); calendar.position.set(104, 5.8, 176); calendar.rotation.y = 0.5; field.add(calendar);
  // newspaper for shot 5
  const paper = sign(['EL DIARIO · 7 DE MAYO DE 1937', 'CAE EL HINDENBURG', '36 MUERTOS · 62 SOBREVIVIENTES'], 3.2, 4.2, { w: 760, h: 1000, bg: '#EDE6D3', fg: '#151515', border: null, font: 'Anton', sizes: [44, 150, 70] });
  field.add(paper);
  // measuring ribbon for shot 3
  const ribbon = new T.Mesh(new T.PlaneGeometry(1, 3), new T.MeshBasicMaterial({ color: 0xF2C230, side: T.DoubleSide, transparent: true, opacity: 0.95 })); field.add(ribbon);
  const ribbonLabel = sign(['245 METROS'], 34, 10, { w: 1024, h: 300, bg: '#F2C230', fg: '#14213D', border: '#14213D' }); field.add(ribbonLabel);
  const aboard = sign(['97 A BORDO'], 26, 9, { w: 1024, h: 340, bg: '#14213D', fg: '#F2C230', border: '#F2C230' }); field.add(aboard);
  const ship = makeShip(); field.add(ship);
  const fire = makeFire(field);
  const crew = ['sailor', 'sailor', 'sailor', 'sailor', 'sailor'].map(w => actor(field, w, 2));
  const hero = actor(field, 'sailor', 2);
  // passengers in windows (shot 3)
  const windowFaces = [0, 1, 2, 3].map(i => actor(field, i % 2 ? 'passenger' : 'captain', 3));
  // static spark + hydrogen leak (shot 10)
  const sparkTex = canvasTex(128, 128, (g) => { const grd = g.createRadialGradient(64, 64, 2, 64, 64, 62); grd.addColorStop(0, '#FFFFFF'); grd.addColorStop(0.25, '#9FD8FF'); grd.addColorStop(1, 'rgba(60,120,255,0)'); g.fillStyle = grd; g.fillRect(0, 0, 128, 128); });
  const spark = new T.Sprite(new T.SpriteMaterial({ map: sparkTex, transparent: true, depthWrite: false, blending: T.AdditiveBlending })); field.add(spark);
  const leakTex = canvasTex(128, 128, (g) => { const grd = g.createRadialGradient(64, 64, 2, 64, 64, 62); grd.addColorStop(0, 'rgba(255,90,220,0.9)'); grd.addColorStop(1, 'rgba(255,90,220,0)'); g.fillStyle = grd; g.fillRect(0, 0, 128, 128); });
  const leaks = Array.from({ length: 14 }, () => { const s = new T.Sprite(new T.SpriteMaterial({ map: leakTex, transparent: true, depthWrite: false })); field.add(s); return s; });
  const leakLabel = sign(['HIDRÓGENO', 'ESCAPANDO'], 22, 11, { w: 1024, h: 512, bg: '#FF5ADC', fg: '#14213D', border: '#14213D' }); field.add(leakLabel);
  const sparkLabel = sign(['¡CHISPA!'], 20, 7, { w: 1024, h: 360, bg: '#9FD8FF', fg: '#14213D', border: '#14213D' }); field.add(sparkLabel);

  function resetField() {
    ship.position.set(0, 0, 0); ship.rotation.set(0, 0, 0); setBurn(ship, 0); updateFire(fire, ship, L, 0, 0);
    [ribbon, ribbonLabel, aboard, paper, spark, leakLabel, sparkLabel, ...leaks].forEach(o => o.visible = false);
    windowFaces.forEach(a => a.grp.visible = false); crew.forEach(a => a.grp.visible = false); hero.grp.visible = false;
  }
  // nose docks at the mast top: nose is at local -x = -L/2
  function shipAtMast(dist = 60, alt = 60, tilt = 0) { ship.position.set(L / 2 + 6 + dist, alt, 0); ship.rotation.set(0, 0, tilt); setBurn(ship, 0); }

  // --- inside the hull: gas cells ---
  const inside = new T.Scene(); inside.fog = new T.Fog(0x2A1E3A, 40, 260);
  inside.background = new T.Color(0x1A1428);
  inside.add(new T.HemisphereLight(0xFFD8F2, 0x221133, 1.4)); { const p = new T.PointLight(0xFFB3E8, 3000, 400); p.position.set(0, 10, 0); inside.add(p); }
  const cells = [];
  { const girder = toon(0x7A6A5A); for (let i = 0; i < 12; i++) { const ring = new T.Mesh(new T.TorusGeometry(19, 0.5, 6, 20), girder); ring.rotation.y = Math.PI / 2; ring.position.x = -110 + i * 20; inside.add(ring); }
    for (let k = 0; k < 10; k++) { const a = k / 10 * Math.PI * 2; if (Math.cos(a) > 0.3) continue; const b = new T.Mesh(new T.BoxGeometry(240, 0.5, 0.5), girder); b.position.set(10, Math.sin(a) * 19, Math.cos(a) * 19); inside.add(b); }
    const cellTex = canvasTex(512, 512, (g, w, h) => { g.fillStyle = '#EADFCB'; g.fillRect(0, 0, w, h); strokes(g, w, h, 300, ['#D9CBB2', '#F5EDDD'], 50, 8); g.fillStyle = '#B3261E'; g.font = '200px Anton'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('H₂', w / 2, h / 2); });
    for (let i = 0; i < 11; i++) { const m = toon(0xffffff, cellTex); m.emissive = new T.Color(0xC2309A); m.emissiveIntensity = 0; const c = new T.Mesh(new T.SphereGeometry(17, 24, 16), m); c.scale.set(0.55, 0.85, 0.85); c.position.x = -100 + i * 20; c.rotation.y = -Math.PI / 2; inside.add(c); cells.push(c); } }
  const heTank = new T.Group(); inside.add(heTank);
  { const tank = new T.Mesh(new T.CylinderGeometry(2.5, 2.5, 9, 20), toon(0x5B8FD1)); heTank.add(tank); const lab = sign(['HELIO'], 6, 2.4, { w: 800, h: 320, bg: '#F3E7C9', fg: '#1F3A68' }); lab.position.set(0, 1, 2.6); heTank.add(lab);
    const x1 = new T.Mesh(new T.BoxGeometry(12, 1.1, 0.4), new T.MeshBasicMaterial({ color: 0xD0261E })); x1.rotation.z = 0.8; x1.position.z = 3; heTank.add(x1); const x2 = x1.clone(); x2.rotation.z = -0.8; heTank.add(x2); heTank.userData.x = [x1, x2]; }
  heTank.position.set(-22, -8, 34); heTank.scale.setScalar(1.6);
  const arde = sign(['UN GAS QUE ARDE'], 34, 8, { w: 1024, h: 250, bg: '#FF3FC8', fg: '#FFFFFF', border: '#14213D' }); inside.add(arde);

  // --- helium office (US) ---
  const office = new T.Scene(); office.background = new T.Color(0x6B3B2A);
  lights(office, [10, 30, 25], 0xFFE9C9, 0x5A3A22, 0xFFE2B0, 40);
  { const floor = new T.Mesh(new T.PlaneGeometry(80, 80), toon(0xffffff, woodTex)); floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; office.add(floor);
    const wallTex = canvasTex(512, 512, (g, w, h) => { g.fillStyle = '#7C9A7E'; g.fillRect(0, 0, w, h); strokes(g, w, h, 500, ['#6E8B70', '#8AA98C'], 40, 8); }, [3, 2]);
    const wall = new T.Mesh(new T.PlaneGeometry(80, 30), toon(0xffffff, wallTex)); wall.position.set(0, 15, -10); wall.receiveShadow = true; office.add(wall);
    const desk = new T.Mesh(new T.BoxGeometry(9, 2.6, 4), toon(0xffffff, woodTex)); desk.position.set(0, 1.3, 2); desk.castShadow = desk.receiveShadow = true; office.add(desk);
    for (let i = 0; i < 7; i++) { const tk = new T.Mesh(new T.CylinderGeometry(0.8, 0.8, 5, 16), toon(0x5B8FD1)); tk.position.set(-9 + i * 3, 2.5, -7.5); tk.castShadow = true; office.add(tk); const cap = new T.Mesh(new T.CylinderGeometry(0.3, 0.3, 0.8, 8), toon(0x333333)); cap.position.set(tk.position.x, 5.4, -7.5); office.add(cap); }
    const big = sign(['HELIO', 'PROPIEDAD DE EE.UU.'], 16, 5, { w: 1024, h: 320, bg: '#F3E7C9', fg: '#1F3A68', border: '#B3261E', sizes: [150, 70] }); big.position.set(0, 9.5, -9.9); office.add(big); }
  const lawDoc = sign(['LEY DEL HELIO', 'ENMIENDA DE 1927', 'NO EXPORTAR SIN PERMISO', 'DEL PRESIDENTE'], 2.6, 3.4, { w: 640, h: 840, bg: '#FAF6EC', fg: '#1B1B1B', border: '#B3261E', sizes: [80, 60, 56, 56] });
  lawDoc.rotation.x = -Math.PI / 2 + 0.05; lawDoc.position.set(0.4, 2.62, 2.4); office.add(lawDoc);
  const official = actor(office, 'official', 4.4); official.grp.position.set(0, 0, -1.5);

  // --- storm ---
  const storm = new T.Scene(); storm.fog = new T.Fog(0x3B4766, 200, 1400);
  makeSky(storm, '#26304A', '#5B6788'); lights(storm, [200, 400, 100], 0x9AA6C8, 0x2A2F3E, 0xC9D3F0, 500);
  const stormCloudMat = toon(0x6F7A96);
  { sd = 404; for (let i = 0; i < 60; i++) { const g = new T.Group(); for (let k = 0; k < 5; k++) { const s = new T.Mesh(new T.SphereGeometry(20 + rnd() * 25, 10, 8), stormCloudMat); s.position.set((rnd() - 0.5) * 80, (rnd() - 0.5) * 20, (rnd() - 0.5) * 50); g.add(s); } g.position.set(-900 + rnd() * 1800, 40 + rnd() * 260, -500 + rnd() * 900); g.scale.setScalar(1 + rnd()); storm.add(g); } }
  const bolts = []; { const m = new T.MeshBasicMaterial({ color: 0xFFF2A0 }); for (let b = 0; b < 5; b++) { const pts = []; let x = 0, y = 0; for (let i = 0; i < 9; i++) { pts.push(new T.Vector3(x, y, 0)); x += (Math.sin(b * 7 + i * 3.1) * 14); y -= 26; } const tube = new T.Mesh(new T.TubeGeometry(new T.CatmullRomCurve3(pts, false, 'catmullrom', 0), 40, 2.4, 5), m); tube.position.set(-400 + b * 200, 260, -200 + (b % 2) * 300); storm.add(tube); bolts.push(tube); } }
  const stormShip = makeShip(); storm.add(stormShip);
  const rain = new T.LineSegments(new T.BufferGeometry(), new T.LineBasicMaterial({ color: 0xB9C6E8, transparent: true, opacity: 0.55 }));
  { const p = []; sd = 9; for (let i = 0; i < 2500; i++) { const x = (rnd() - 0.5) * 1400, y = rnd() * 500, z = (rnd() - 0.5) * 1200; p.push(x, y, z, x + 3, y - 18, z); } rain.geometry.setAttribute('position', new T.Float32BufferAttribute(p, 3)); storm.add(rain); }
  const lateSign = sign(['+12 HORAS', 'DE ATRASO'], 3.2, 2, { w: 800, h: 500, bg: '#F2C230', fg: '#14213D', border: '#14213D' });
  const captain = actor(storm, 'captain', 3);

  // --- investigation room ---
  const room = new T.Scene(); room.background = new T.Color(0x2E2A2A);
  lights(room, [0, 30, 15], 0xFFE6C0, 0x3A2A1A, 0xFFE0A8, 30);
  { const fl = new T.Mesh(new T.PlaneGeometry(60, 60), toon(0xffffff, woodTex)); fl.rotation.x = -Math.PI / 2; fl.receiveShadow = true; room.add(fl);
    const wTex = canvasTex(512, 512, (g, w, h) => { g.fillStyle = '#5C6B7A'; g.fillRect(0, 0, w, h); strokes(g, w, h, 500, ['#53616F', '#687888'], 40, 8); }, [3, 2]);
    const wall = new T.Mesh(new T.PlaneGeometry(60, 25), toon(0xffffff, wTex)); wall.position.set(0, 12.5, -8); room.add(wall);
    const table = new T.Mesh(new T.BoxGeometry(12, 0.5, 5), toon(0xffffff, woodTex)); table.position.set(0, 2.6, 1.5); table.castShadow = table.receiveShadow = true; room.add(table);
    [[-5.5, -0.8], [5.5, -0.8], [-5.5, 3.8], [5.5, 3.8]].forEach(([x, z]) => { const l = new T.Mesh(new T.BoxGeometry(0.4, 2.6, 0.4), toon(0xffffff, woodTex)); l.position.set(x, 1.3, z); room.add(l); });
    const burnt = toon(0x2A1A12); room.userData.girders = []; for (let i = 0; i < 6; i++) { const g = new T.Mesh(new T.BoxGeometry(2.5 + i % 3, 0.25, 0.25), burnt); g.position.set(-2 + i * 0.8, 2.95, 1 + (i % 2) * 0.8); g.rotation.y = i * 0.7; g.castShadow = true; room.add(g); room.userData.girders.push(g); }
    const lamp = new T.Mesh(new T.ConeGeometry(1.4, 1.2, 16, 1, true), toon(0x2E4A3A)); lamp.position.set(0, 9, 1.5); room.add(lamp);
    const de = sign(['ALEMANIA'], 3.2, 1.1, { w: 800, h: 270, bg: '#F3E7C9', fg: '#14213D' }); de.position.set(-2.3, 3.4, 3.9); de.rotation.x = -0.3; room.add(de);
    const us = sign(['EE.UU.'], 3.2, 1.1, { w: 800, h: 270, bg: '#F3E7C9', fg: '#14213D' }); us.position.set(2.3, 3.4, 3.9); us.rotation.x = -0.3; room.add(us);
    const concl = sign(['MISMA', 'CONCLUSIÓN'], 6, 3, { w: 900, h: 450, bg: '#B3261E', fg: '#FFFFFF', border: '#14213D' }); concl.position.set(0, 7.5, -7.9); room.add(concl); room.userData.concl = concl; }
  const folder = sign(['INFORME FINAL', 'SIN PRUEBA', 'DIRECTA'], 2.6, 3.2, { w: 640, h: 800, bg: '#E3C58A', fg: '#B3261E', border: '#B3261E', sizes: [60, 150, 150] }); folder.rotation.x = -Math.PI / 2 + 0.02; folder.position.set(0, 2.88, 2.6); room.add(folder);
  const invDE = actor(room, 'german', 5.4); invDE.grp.position.set(-2.3, 0, -0.6);
  const invUS = actor(room, 'american', 5.4); invUS.grp.position.set(2.3, 0, -0.6);

  // ---------- camera helpers ----------
  const cam = new T.PerspectiveCamera(50, W / H, 0.1, 9000);
  const ease = x => x < 0 ? 0 : x > 1 ? 1 : x * x * (3 - 2 * x);
  const lerp = (a, b, k) => a + (b - a) * k;
  const V = (x, y, z) => new T.Vector3(x, y, z);
  const lerpV = (a, b, k) => a.clone().lerp(b, k);
  function place(pos, look, fov = 50, roll = 0) { cam.position.copy(pos); cam.fov = fov; cam.updateProjectionMatrix(); cam.up.set(0, 1, 0); cam.lookAt(look); if (roll) cam.rotateZ(roll); }

  // ---------- shots: each returns the scene to render ----------
  const shots = [
    // 1 — hook: low along the ground, crane up to the ship over the mast
    (t, d) => { resetField(); const u = ease(t / d);
      shipAtMast(40 - u * 10, 62); hero.grp.visible = true; hero.grp.position.set(70, 0, 30); hero.set(u > 0.45 ? 'surprised' : 'neutral', u > 0.45 ? 'up' : 'down'); hero.bob(t);
      crew.forEach((a, i) => { a.grp.visible = true; a.grp.position.set(30 + i * 14, 0, -30 + i * 9); a.set(i % 2 ? 'worried' : 'neutral'); a.bob(t + i); });
      place(lerpV(V(110, 1.6, 52), V(96, 8, 44), u), lerpV(V(70, 2.2, 30), V(40, 62, 0), ease((t - 0.6) / (d - 0.6))), lerp(42, 60, u), -0.05 + u * 0.08); return field; },
    // 2 — date/place: dolly from the gate sign to the calendar on the crate
    (t, d) => { resetField(); const u = ease(t / d); shipAtMast(35, 62);
      place(lerpV(V(160, 16, 200), V(112, 6.4, 188), u), lerpV(V(120, 9, 160), V(104, 5.6, 176), ease((t - 0.8) / 1.8)), lerp(55, 42, u), 0.03); return field; },
    // 3 — 245 m: track along the hull, yellow ribbon grows; then 97 aboard at the windows
    (t, d) => { resetField(); const u = ease(t / d); shipAtMast(30, 62);
      const grow = ease(t / 1.6); ribbon.visible = true; ribbon.scale.set(L * grow, 1, 1); ribbon.position.set(L / 2 + 36 - L * grow / 2 + 0, 62 - R - 4, R + 2); ribbon.rotation.set(0, 0, 0);
      ribbonLabel.visible = grow > 0.95; ribbonLabel.position.set(L / 2 + 36 - L / 2, 62 - R - 14, R + 3);
      const late = ease((t - 2.1) / 1.2); aboard.visible = late > 0; aboard.position.set(-20, 62 - R - 10, R + 6); aboard.scale.setScalar(Math.max(0.01, late));
      windowFaces.forEach((a, i) => { a.grp.visible = late > 0; a.grp.position.set(-30 + i * 9, 62 - R * 0.62 - 1.2, R + 2); a.set(['happy', 'smug', 'happy', 'neutral'][i]); });
      const p = lerpV(V(160, 30, 440), V(10, 44, 110), u); place(p, lerpV(V(158, 56, 0), V(-24, 42, R), u), 52, 0.05 - u * 0.05); return field; },
    // 4 — 34 seconds: fire runs tail→nose, tail sinks, ship falls; camera orbits low
    (t, d) => { resetField(); const b = ease(t / (d * 0.9));
      shipAtMast(30, 62 - b * 52, b * 0.35); const cut = setBurn(ship, b); updateFire(fire, ship, cut, t, 1);
      hero.grp.visible = true; hero.grp.position.set(150, 0, 110); hero.set('surprised', 'up'); hero.bob(t, 0.08);
      const a = 0.9 - t / d * 0.7; place(V(Math.cos(a) * 260 + 120, 10 + t * 2, Math.sin(a) * 260), V(130, 35 - b * 25, 0), 55, 0.04); return field; },
    // 5 — 36 dead, 62 survived: wreck on the ground; newspaper flies in to camera
    (t, d) => { resetField(); ship.position.set(L / 2 + 36, 10, 0); ship.rotation.set(0, 0, 0.12); setBurn(ship, 1); updateFire(fire, ship, -L / 2, t, 0.55, true);
      crew.forEach((a, i) => { a.grp.visible = true; a.grp.position.set(40 + i * 25, 0, 60 + (i % 2) * 15); a.set(i % 2 ? 'sad' : 'worried'); a.bob(t + i, 0.03); });
      const u = ease(t / d); const cp = lerpV(V(260, 18, 160), V(230, 9, 120), u); const tgt = V(130, 8, 0); place(cp, tgt, 50, -0.03);
      const pin = ease((t - 0.6) / 1.0); paper.visible = pin > 0; const dir = tgt.clone().sub(cp).normalize();
      const pp = cp.clone().add(dir.multiplyScalar(lerp(40, 6.2, pin))); pp.y += lerp(8, 1.1, pin); paper.position.copy(pp); paper.quaternion.copy(cam.quaternion); paper.rotateZ(lerp(1.4, 0.05, pin)); return field; },
    // 6 — inside: hydrogen cells glow, helium tank crossed out
    (t, d) => { const u = ease(t / d); cells.forEach((c, i) => { c.material.emissiveIntensity = ease((t - 1.6 - i * 0.05) / 0.6) * (0.55 + 0.15 * Math.sin(t * 6 + i)); });
      heTank.visible = t < 2.2; heTank.userData.x.forEach(x => x.visible = t > 0.9); arde.visible = t > 2.6; arde.position.set(lerp(-40, -66, u), 24, 22); arde.lookAt(cam.position);
      place(lerpV(V(10, -8, 95), V(-70, 4, 78), u), lerpV(V(-20, -4, 0), V(-80, 0, 0), u), 55, 0.05 * Math.sin(t)); return inside; },
    // 7 — US helium office; the official guards the law, gets angry, push to face
    (t, d) => { const u = ease(t / d); const angry = t > d * 0.55;
      official.set(angry ? 'angry' : (t > 1.2 ? 'smug' : 'neutral'), angry ? 'hips' : 'down', angry ? { angry: true } : {}); official.bob(t, 0.02);
      const look = lerpV(V(0, 2.8, 1), V(0, 3.4, -1.3), ease((t - 2.6) / 2));
      place(lerpV(V(7, 6, 14), V(0.4, 3.6, 4.2), u), look, lerp(50, 40, u), lerp(-0.06, 0.02, u)); return office; },
    // 8 — storm: ship crosses a charged front; captain checks the watch
    (t, d) => { const u = ease(t / d); stormShip.position.set(lerp(-250, 200, t / d), 200, 0); stormShip.rotation.set(0, Math.PI, 0.03 * Math.sin(t));
      const pose = Math.floor(t * 12); bolts.forEach((b, i) => { b.visible = ((pose * 7 + i * 13) % 11) < 2; });
      rain.position.y = -((t * 400) % 18);
      captain.grp.visible = t > 2.6; captain.set('worried', 'hold', { prop: 'watch' });
      if (captain.grp.visible) { const fwd = new T.Vector3(); cam.getWorldDirection(fwd); }
      if (t < 2.6) { place(lerpV(V(-100, 230, 260), V(40, 215, 170), u), stormShip.position.clone(), 55, 0.12); storm.remove(lateSign); }
      else { const k = ease((t - 2.6) / (d - 2.6)); place(V(0, 1.7, lerp(8, 5.5, k)), V(0, 1.6, 0), 45, 0.04); captain.grp.position.set(-0.2, 0, 0); captain.bob(t, 0.02); lateSign.position.set(1.6, 2.2, 1); lateSign.rotation.set(0, -0.3, 0.06); storm.add(lateSign); }
      return storm; },
    // 9 — two investigations, same conclusion
    (t, d) => { const u = ease(t / d); invDE.set(t > 1.6 ? 'smug' : 'neutral', 'hold', { prop: t > 0.8 ? 'magnifier' : null }); invUS.set(t > 1.9 ? 'smug' : 'neutral', 'hips'); invDE.bob(t, 0.02); invUS.bob(t + 1, 0.02);
      room.userData.concl.visible = t > 1.4; folder.visible = false; room.userData.girders.forEach(g => g.visible = true);
      place(lerpV(V(-5, 5.2, 12.5), V(3, 5, 11.5), u), V(0, 3.4, -0.6), 50, lerp(0.05, -0.04, u)); return room; },
    // 10 — the leading theory: leak + static spark at the tail
    (t, d) => { resetField(); shipAtMast(26, 62); const u = ease(t / d);
      leaks.forEach((s, i) => { s.visible = true; const k = ((t * 0.5 + i / 14) % 1); s.position.set(L / 2 + 26 + 40 + (i % 5) * 4, 62 + R * 0.8 + k * 30, -4 + (i % 3) * 4); s.scale.setScalar(6 + k * 12); s.material.opacity = 1 - k; });
      leakLabel.visible = t > 0.8; leakLabel.position.set(L / 2 + 26 + 40, 62 + R + 38, 0); leakLabel.lookAt(cam.position);
      const pose = Math.floor(t * 12); spark.visible = t > 1.8 && pose % 3 !== 0; spark.position.set(L / 2 + 26 + 60, 62 + R * 0.7, 6); spark.scale.setScalar(14 + (pose % 4) * 4);
      sparkLabel.visible = t > 2.0; sparkLabel.position.set(L / 2 + 26 + 78, 62 + R * 0.4, 18); sparkLabel.lookAt(cam.position);
      place(lerpV(V(L / 2 + 140, 120, 160), V(L / 2 + 110, 92, 70), u), V(L / 2 + 26 + 55, 62 + R * 0.6, 0), 52, 0.07); return field; },
    // 11 — but no direct proof: investigator shrugs, push into the folder
    (t, d) => { const u = ease(t / d); room.userData.concl.visible = false; folder.visible = true; room.userData.girders.forEach(g => g.visible = false);
      invUS.set(t > 0.6 ? 'worried' : 'neutral', t > 0.6 ? 'up' : 'down'); invDE.set('sad', 'down'); invUS.bob(t, 0.04); invDE.bob(t + 1, 0.02);
      place(lerpV(V(0, 8, 13), V(0, 6.2, 5.2), u), lerpV(V(0, 4, -1), V(0, 2.9, 2.6), ease((t - 1) / (d - 1))), 48, -0.03); return room; },
    // 12 — one spark, end of an era: burning ship over the field, crane up and back
    (t, d) => { resetField(); const b = 0.25 + 0.6 * ease(t / d); shipAtMast(30, 62 - b * 30, b * 0.3); const cut = setBurn(ship, b); updateFire(fire, ship, cut, t, 1);
      hero.grp.visible = true; hero.grp.position.set(260, 0, 140); hero.set('sad', 'down'); hero.bob(t, 0.02);
      const u = ease(t / d); place(lerpV(V(275, 2.2, 152), V(340, 70, 260), u), lerpV(V(240, 6, 120), V(120, 40, 0), u), lerp(45, 58, u), 0.03); return field; },
  ];

  // ---------- captions ----------
  const out = document.getElementById('c'); out.width = W; out.height = H; const o2 = out.getContext('2d');
  function captionAt(t) {
    let words = WORDS;
    if (!words) { // estimate from script lines, evenly by characters
      words = []; SCRIPT.forEach((line, i) => { const s = SHOTS[i] + 0.15, e = SHOTS[i + 1] - 0.25; const ws = line.split(/\s+/); const tot = ws.reduce((a, w) => a + w.length + 2, 0); let acc = s; ws.forEach(w => { const dur = (e - s) * (w.length + 2) / tot; words.push({ w, s: acc, e: acc + dur }); acc += dur; }); });
      window.WORD_TIMES = WORDS || words;
    }
    // group into chunks of up to 3 words, breaking after punctuation
    const chunks = []; let cur = [];
    words.forEach((w, i) => { cur.push(w); const punct = /[.,:?!]$/.test(w.w); if (cur.length === 3 || punct || i === words.length - 1) { chunks.push(cur); cur = []; } });
    const ch = chunks.find((c, i) => t >= c[0].s && t < (chunks[i + 1] ? Math.min(chunks[i + 1][0].s, c[c.length - 1].e + 0.6) : c[c.length - 1].e + 0.8));
    if (!ch) return null; return ch.filter(w => w.s <= t + 0.02).map(w => w.w).join(' ');
  }
  function drawCaption(txt) {
    if (!txt) return; let s = 118; o2.font = `900 ${s}px Montserrat`; while (o2.measureText(txt).width > 940) { s -= 4; o2.font = `900 ${s}px Montserrat`; }
    o2.textAlign = 'center'; o2.textBaseline = 'middle'; const x = W / 2, y = H * 0.57;
    o2.lineJoin = 'round'; o2.shadowColor = 'rgba(0,0,0,0.55)'; o2.shadowBlur = 14; o2.shadowOffsetY = 6;
    o2.strokeStyle = '#000'; o2.lineWidth = 14; o2.strokeText(txt, x, y); o2.shadowColor = 'transparent';
    o2.fillStyle = '#fff'; o2.fillText(txt, x, y);
  }

  // ---------- frame assembly (whip transitions with motion blur) ----------
  function shotIndex(t) { let i = 0; while (i < shots.length - 1 && t >= SHOTS[i + 1]) i++; return i; }
  const WHIP = 0.28;
  function renderShot(i, lt) {
    const d = SHOTS[i + 1] - SHOTS[i]; const scene = shots[i](lt, d);
    // whip yaw at the cut
    let yaw = 0; if (lt > d - WHIP && i < shots.length - 1) yaw = Math.pow((lt - (d - WHIP)) / WHIP, 2) * 1.1; if (lt < WHIP && i > 0) yaw = -Math.pow((WHIP - lt) / WHIP, 2) * 1.1;
    if (yaw) cam.rotateY(-yaw);
    renderer.setRenderTarget(rt); renderer.setViewport(0, 0, RW, RH); renderer.render(scene, cam); renderer.setViewport(0, 0, W, H); renderer.setRenderTarget(null); renderer.render(postScene, postCam);
  }
  function blit(alpha) { o2.globalAlpha = alpha; o2.drawImage(glCanvas, 0, 0); o2.globalAlpha = 1; }
  function frame(t) {
    t = Math.max(0, Math.min(DURATION - 1e-4, t));
    const i = shotIndex(t); const lt = t - SHOTS[i]; const d = SHOTS[i + 1] - SHOTS[i];
    const nearCut = (lt > d - WHIP && i < shots.length - 1) || (lt < WHIP && i > 0);
    o2.fillStyle = '#000'; o2.fillRect(0, 0, W, H);
    if (!nearCut) { renderShot(i, lt); blit(1); }
    else { const N = 7; for (let k = 0; k < N; k++) { const tt = Math.max(0, Math.min(DURATION - 1e-4, t + (k - (N - 1) / 2) * (1 / FPS / N) * 1.6)); const j = shotIndex(tt); renderShot(j, tt - SHOTS[j]); blit(1 / (k + 1)); } }
    drawCaption(captionAt(t));
  }
  window.DURATION = DURATION; window.FPS = FPS; window.seek = frame;
})();
