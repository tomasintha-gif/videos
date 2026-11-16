"""Procedural painterly assets: sky, ground, trees, props and 2D characters."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageChops

HERE = __file__.rsplit('/', 1)[0]
FONT = HERE + '/assets/montserrat-latin-800-normal.woff'
INK = (22, 18, 20, 255)


def font(sz):
    return ImageFont.truetype(FONT, sz)


def rng(seed):
    return random.Random(seed)


# ---------------------------------------------------------------- helpers
def wobble_poly(cx, cy, rx, ry, seed, n=48, amp=0.035):
    r = rng(seed)
    ph = [r.uniform(0, 6.28) for _ in range(3)]
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        k = 1 + amp * (math.sin(3 * a + ph[0]) + 0.6 * math.sin(5 * a + ph[1]) + 0.4 * math.sin(7 * a + ph[2]))
        pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    return pts


def outline(d, pts, w=14, col=INK, closed=True):
    p = list(pts) + ([pts[0], pts[1]] if closed else [])
    d.line(p, fill=col, width=w, joint='curve')
    for x, y in (pts if not closed else []):
        pass


def strokes(img, box, cols, n, seed, size=(10, 30), alpha=200, angle=None, mask=None):
    """Paint short brush strokes into box using palette cols."""
    r = rng(seed)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, y0, x1, y1 = box
    for _ in range(n):
        x = r.uniform(x0, x1); y = r.uniform(y0, y1)
        L = r.uniform(*size); a = angle if angle is not None else r.uniform(0, math.pi)
        a += r.uniform(-0.3, 0.3)
        c = r.choice(cols)
        wdt = max(2, int(L * r.uniform(0.18, 0.35)))
        d.line([(x - L / 2 * math.cos(a), y - L / 2 * math.sin(a)), (x + L / 2 * math.cos(a), y + L / 2 * math.sin(a))],
               fill=c[:3] + (alpha,), width=wdt)
    if mask is not None:
        lay.putalpha(ImageChops.multiply(lay.getchannel('A'), mask))
    img.alpha_composite(lay)


def posterize(img, bits=5):
    a = img.getchannel('A') if img.mode == 'RGBA' else None
    rgb = ImageOps.posterize(img.convert('RGB'), bits)
    if a is not None:
        rgb = rgb.convert('RGBA'); rgb.putalpha(a)
    return rgb


def shrink(img, f=2):
    return img.resize((img.width // f, img.height // f), Image.LANCZOS)


# ---------------------------------------------------------------- sky
def make_sky(kind='day', W=4096, H=1024):
    """Panorama: x=azimuth 0..2pi, y=elev from +1.35 rad (top) to -0.25 (bottom)."""
    y = np.linspace(0, 1, H)[:, None]
    if kind == 'day':
        top = np.array([20, 62, 168]); hor = np.array([120, 178, 235])
    elif kind == 'dawn':
        top = np.array([44, 78, 170]); hor = np.array([255, 196, 150])
    else:  # night
        top = np.array([6, 10, 34]); hor = np.array([34, 52, 110])
    t = np.clip(y / 0.86, 0, 1) ** 1.6
    col = top * (1 - t) + hor * t
    arr = np.repeat(col[:, None, :], W, axis=1).astype(np.float32)
    img = Image.fromarray(arr.astype(np.uint8)).convert('RGBA')
    r = rng(7 if kind == 'day' else 8)
    d = ImageDraw.Draw(img)
    if kind == 'night':
        for _ in range(900):
            x = r.uniform(0, W); yy = r.uniform(0, H * 0.75); s = r.choice([1, 1, 1, 2, 2, 3])
            c = r.randint(170, 255)
            d.ellipse([x - s, yy - s, x + s, yy + s], fill=(c, c, 255, 255))
        # moon
        mx, my = W * 0.62, H * 0.28
        for k in range(30, 0, -1):
            a = int(5 * (30 - k) / 30 + 1)
            d.ellipse([mx - 60 - k * 6, my - 60 - k * 6, mx + 60 + k * 6, my + 60 + k * 6], fill=(150, 170, 255, a))
        d.ellipse([mx - 60, my - 60, mx + 60, my + 60], fill=(240, 240, 220, 255))
        d.ellipse([mx - 20, my - 30, mx + 5, my - 5], fill=(215, 215, 200, 255))
        d.ellipse([mx + 15, my + 10, mx + 35, my + 30], fill=(220, 220, 205, 255))
    # streaky clouds
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ncl = 34 if kind != 'night' else 16
    for i in range(ncl):
        cx = r.uniform(0, W); cy = r.uniform(H * 0.15, H * 0.7)
        L = r.uniform(250, 700); th = r.uniform(18, 50) * (0.6 + cy / H)
        if kind == 'day':
            cols = [(255, 255, 255), (232, 240, 252), (196, 212, 240), (170, 190, 230)]
        elif kind == 'dawn':
            cols = [(255, 236, 220), (255, 206, 190), (236, 170, 180), (180, 150, 190)]
        else:
            cols = [(70, 84, 140), (56, 66, 118), (90, 100, 150)]
        for k in range(14):
            ox = r.uniform(-L / 2, L / 2); oy = r.uniform(-th, th) * 0.8
            w = r.uniform(L * 0.15, L * 0.45); h = th * r.uniform(0.4, 1.0)
            c = cols[min(len(cols) - 1, int((oy + th) / (2 * th) * len(cols)))]
            for dx in (-W, 0, W):
                ld.ellipse([cx + ox - w + dx, cy + oy - h, cx + ox + w + dx, cy + oy + h], fill=c + (235,))
    lay = lay.filter(ImageFilter.GaussianBlur(2))
    strokes(lay, (0, 0, W, H), [(255, 255, 255)] if kind == 'day' else [(255, 230, 220)], 5000, 3, (20, 60), 60, angle=0.02,
            mask=lay.getchannel('A'))
    img.alpha_composite(lay)
    strokes(img, (0, 0, W, H), [tuple(int(v) for v in top), tuple(int(v) for v in hor)], 6000, 5, (30, 90), 40, angle=0.0)
    return posterize(img, 5).convert('RGB')


# ---------------------------------------------------------------- ground
def make_ground(W=2048):
    """World ground map: covers x in [-64,64], z in [-40,88] (16 px/m)."""
    img = Image.new('RGBA', (W, W), (118, 150, 52, 255))
    strokes(img, (0, 0, W, W), [(96, 132, 40), (138, 166, 62), (160, 172, 70), (84, 116, 36), (122, 140, 46)], 60000, 11,
            (8, 22), 230)
    d = ImageDraw.Draw(img)

    def wx(x): return (x + 64) * 16

    def wz(z): return (z + 40) * 16
    # dirt rows under trees on both farms
    soil = [(150, 92, 52), (128, 74, 42), (170, 108, 60), (112, 64, 38)]
    for side in (-1, 1):
        for i in range(6):
            x = side * (5 + i * 6)
            box = (wx(x - 1.6), wz(-4), wx(x + 1.6), wz(62))
            d.rectangle(box, fill=(140, 86, 48, 255))
            strokes(img, box, soil, 2200, 100 + i * 7 + side, (6, 18), 255, angle=math.pi / 2)
    # road between farms (along z) at x in [-1.5, 1.5]
    box = (wx(-1.6), wz(-40), wx(1.6), wz(88))
    d.rectangle(box, fill=(186, 140, 90, 255))
    strokes(img, box, [(200, 156, 100), (170, 124, 80), (214, 170, 116), (150, 106, 70)], 9000, 21, (6, 16), 255,
            angle=math.pi / 2)
    # farmyard near houses
    for side in (-1, 1):
        box = (wx(side * 6 - 9), wz(-16), wx(side * 6 + 9), wz(-7))
        box = (min(box[0], box[2]), box[1], max(box[0], box[2]), box[3])
        strokes(img, box, [(176, 132, 84), (156, 112, 72), (190, 150, 96)], 3000, 31 + side, (6, 16), 220)
    return posterize(img, 5).convert('RGB')


def make_detail(S=256):
    img = Image.new('RGBA', (S, S), (128, 128, 128, 255))
    strokes(img, (0, 0, S, S), [(100, 100, 100), (150, 150, 150), (120, 120, 120), (165, 165, 165)], 900, 5, (4, 12), 200)
    return img.convert('L')


# ---------------------------------------------------------------- trees
def _canopy_mask(W, H, cx, cy, R, seed):
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    r = rng(seed)
    blobs = []
    for i in range(9):
        a = 2 * math.pi * i / 9 + r.uniform(-0.2, 0.2)
        rr = R * r.uniform(0.42, 0.55)
        bx = cx + math.cos(a) * R * 0.55; by = cy + math.sin(a) * R * 0.45
        blobs.append((bx, by, rr))
    blobs.append((cx, cy, R * 0.7))
    for bx, by, rr in blobs:
        d.polygon(wobble_poly(bx, by, rr, rr, r.randint(0, 999), 40, 0.05), fill=255)
    return m, blobs


def make_tree(state='normal', seed=1, broken=False):
    """state: normal | ice | blanket. Returns RGBA ~ 512x640 (trunk base at bottom center)."""
    S = 2
    W, H = 512 * S, 640 * S
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    r = rng(seed)
    cx, cy, R = W / 2, H * 0.40, W * 0.40
    # trunk
    tw = W * 0.07
    trunk = [(cx - tw, H - 4 * S), (cx - tw * 0.6, cy + R * 0.3), (cx - tw * 1.8, cy), (cx - tw * 0.2, cy + R * 0.2),
             (cx + tw * 1.6, cy - R * 0.1), (cx + tw * 0.6, cy + R * 0.35), (cx + tw, H - 4 * S)]
    d.polygon(trunk, fill=(118, 70, 40, 255))
    strokes(img, (cx - tw * 2, cy, cx + tw * 2, H), [(90, 52, 30), (140, 88, 52), (70, 40, 24)], 300, seed, (8 * S, 24 * S),
            255, angle=math.pi / 2, mask=img.getchannel('A'))
    outline(d, trunk, 7 * S)
    mask, blobs = _canopy_mask(W, H, cx, cy, R, seed)
    can = Image.new('RGBA', (W, H), (46, 104, 44, 255))
    strokes(can, (cx - R * 1.2, cy - R * 1.2, cx + R * 1.2, cy + R * 1.2),
            [(34, 82, 36), (58, 124, 50), (28, 66, 30), (74, 140, 58)], 1600, seed + 1, (10 * S, 34 * S), 255)
    # sunlit upper-left, shade lower-right
    g = np.zeros((H, W, 4), np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    lit = np.clip(1 - np.hypot(xx - (cx - R * 0.45), yy - (cy - R * 0.5)) / (R * 1.0), 0, 1)
    g[..., 0] = 150; g[..., 1] = 196; g[..., 2] = 70; g[..., 3] = (lit ** 1.5 * 150).astype(np.uint8)
    can.alpha_composite(Image.fromarray(g))
    sh = np.clip(np.hypot(xx - (cx + R * 0.5), yy - (cy + R * 0.6)) < R * 0.9, 0, 1)
    g2 = np.zeros((H, W, 4), np.uint8); g2[..., 0] = 10; g2[..., 1] = 40; g2[..., 2] = 40
    g2[..., 3] = (sh * 90).astype(np.uint8)
    can.alpha_composite(Image.fromarray(g2))
    strokes(can, (cx - R, cy - R, cx + R * 0.2, cy), [(120, 178, 70), (98, 160, 60)], 400, seed + 2, (8 * S, 22 * S), 230)
    # oranges
    cd = ImageDraw.Draw(can)
    oranges = []
    for i in range(16):
        a = r.uniform(0, 6.28); rr = R * math.sqrt(r.uniform(0.05, 0.75))
        ox = cx + math.cos(a) * rr; oy = cy + math.sin(a) * rr * 0.85
        orr = R * r.uniform(0.075, 0.095)
        oranges.append((ox, oy, orr))
    for ox, oy, orr in oranges:
        cd.ellipse([ox - orr, oy - orr, ox + orr, oy + orr], fill=(246, 128, 20, 255), outline=INK, width=4 * S)
        cd.ellipse([ox - orr * 0.55, oy - orr * 0.6, ox - orr * 0.05, oy - orr * 0.15], fill=(255, 200, 90, 255))
        cd.ellipse([ox + orr * 0.1, oy + orr * 0.2, ox + orr * 0.7, oy + orr * 0.7], fill=(214, 92, 14, 255))
    can.putalpha(mask)
    img.alpha_composite(can)
    # canopy outline
    edge = mask.filter(ImageFilter.MaxFilter(9)); inner = mask.filter(ImageFilter.MinFilter(3))
    ring = ImageChops.subtract(edge, inner)
    ol = Image.new('RGBA', (W, H), (18, 34, 20, 255)); ol.putalpha(ring)
    img.alpha_composite(ol)
    if broken:
        # a branch snapped and hanging down on the right
        bx0, by0 = cx + R * 0.55, cy + R * 0.25
        br = [(bx0, by0), (bx0 + R * 0.25, by0 + R * 0.15), (bx0 + R * 0.35, by0 + R * 0.75), (bx0 + R * 0.28, by0 + R * 0.78),
              (bx0 + R * 0.15, by0 + R * 0.25), (bx0 - 6 * S, by0 + 10 * S)]
        d2 = ImageDraw.Draw(img)
        d2.polygon(br, fill=(118, 70, 40, 255)); outline(d2, br, 6 * S)
        for k in range(6):
            lx = bx0 + R * 0.3 + r.uniform(-R * 0.12, R * 0.12); ly = by0 + R * (0.3 + 0.08 * k)
            d2.polygon(wobble_poly(lx, ly, R * 0.1, R * 0.08, k), fill=(46, 104, 44, 255), outline=INK)
        d2.ellipse([bx0 + R * 0.22, by0 + R * 0.62, bx0 + R * 0.4, by0 + R * 0.8], fill=(246, 128, 20, 255), outline=INK,
                   width=4 * S)
        # splinters
        d2.polygon([(bx0 - 10 * S, by0 - 8 * S), (bx0 + 12 * S, by0 - 26 * S), (bx0 + 8 * S, by0 + 4 * S)],
                   fill=(230, 200, 150, 255), outline=INK)
    if state == 'ice':
        a = img.getchannel('A')
        ice = Image.new('RGBA', (W, H), (190, 228, 255, 0))
        ia = a.point(lambda v: int(v * 0.38))
        ice.putalpha(ia)
        img.alpha_composite(ice)
        strokes(img, (cx - R * 1.1, cy - R * 1.1, cx + R * 1.1, cy + R), [(255, 255, 255), (220, 244, 255)], 260, seed + 5,
                (8 * S, 26 * S), 190, mask=a)
        # glassy highlight arcs
        dg = ImageDraw.Draw(img)
        dg.arc([cx - R * 0.95, cy - R * 0.95, cx + R * 0.95, cy + R * 0.9], 200, 290, fill=(255, 255, 255, 230), width=10 * S)
        dg.arc([cx - R * 0.8, cy - R * 0.8, cx + R * 0.8, cy + R * 0.75], 210, 260, fill=(255, 255, 255, 200), width=6 * S)
        di = ImageDraw.Draw(img)
        # icicles under canopy blobs and branch
        for bx, by, rr in blobs:
            for k in range(4):
                ix = bx + r.uniform(-rr * 0.8, rr * 0.8); iy = by + rr * r.uniform(0.6, 0.9)
                L = r.uniform(30, 90) * S; w = r.uniform(7, 13) * S
                di.polygon([(ix - w, iy), (ix + w, iy), (ix + r.uniform(-4, 4), iy + L)], fill=(225, 245, 255, 245),
                           outline=(60, 110, 160, 255))
                di.line([(ix - w * 0.4, iy + 4), (ix, iy + L * 0.7)], fill=(255, 255, 255, 255), width=2 * S)
        # sparkles
        for k in range(40):
            sx = cx + r.uniform(-R, R); sy = cy + r.uniform(-R, R)
            if a.getpixel((int(sx), int(sy))) > 0:
                s = r.uniform(6, 14) * S
                di.line([(sx - s, sy), (sx + s, sy)], fill=(255, 255, 255, 255), width=2 * S)
                di.line([(sx, sy - s), (sx, sy + s)], fill=(255, 255, 255, 255), width=2 * S)
        # icy ground ring
        di.ellipse([cx - R * 0.6, H - 26 * S, cx + R * 0.6, H], fill=(200, 236, 255, 200))
    if state == 'blanket':
        db = ImageDraw.Draw(img)
        bl = [(cx - R * 1.05, cy + R * 0.55), (cx - R * 0.95, cy - R * 0.55), (cx - R * 0.4, cy - R * 0.98),
              (cx + R * 0.4, cy - R * 0.98), (cx + R * 0.95, cy - R * 0.55), (cx + R * 1.05, cy + R * 0.55)]
        # wavy bottom hem
        for i in range(10, -1, -1):
            x = cx - R * 1.05 + i * R * 0.21
            bl.append((x, cy + R * 0.55 + (14 * S if i % 2 else -4 * S)))
        bm = Image.new('L', (W, H), 0); ImageDraw.Draw(bm).polygon(bl, fill=255)
        quilt = Image.new('RGBA', (W, H), (0, 0, 0, 255)); qd = ImageDraw.Draw(quilt)
        pal = [(176, 52, 44), (214, 160, 60), (64, 96, 150), (150, 90, 60), (196, 92, 60), (90, 130, 120)]
        q = 46 * S
        for i in range(int(W / q) + 1):
            for j in range(int(H / q) + 1):
                qd.rectangle([i * q, j * q, (i + 1) * q, (j + 1) * q], fill=pal[(i * 3 + j * 5 + seed) % len(pal)] + (255,))
                qd.line([(i * q + 6, j * q + 6), ((i + 1) * q - 6, j * q + 6)], fill=(250, 240, 220, 255), width=2 * S)
        strokes(quilt, (0, 0, W, H), [(0, 0, 0), (255, 255, 255)], 1200, seed, (6 * S, 18 * S), 40)
        # fold shading
        quilt.putalpha(bm)
        img.alpha_composite(quilt)
        outline(db, bl, 7 * S)
        # rope around trunk
        db.line([(cx - tw * 1.3, cy + R * 0.75), (cx + tw * 1.3, cy + R * 0.7)], fill=(200, 170, 110, 255), width=6 * S)
    return posterize(shrink(img, S), 5)


def make_spray(seed, W=512, H=420):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); r = rng(seed)
    cx = W / 2; by = H - 6
    for k in range(9):
        a = math.radians(-160 + k * 17.5 + r.uniform(-4, 4))
        v = r.uniform(0.85, 1.0)
        pts = []
        for i in range(30):
            t = i / 29
            x = cx + math.cos(a) * W * 0.48 * t * v
            y = by - math.sin(-a) * H * 1.6 * t * v + H * 1.25 * t * t * v
            pts.append((x, y))
        d.line(pts, fill=(220, 240, 255, 150), width=4)
        for i in range(0, 30, 3):
            x, y = pts[i]
            s = r.uniform(2, 5)
            ox, oy = r.uniform(-6, 6), r.uniform(-6, 6)
            d.ellipse([x - s + ox, y - s + oy, x + s + ox, y + s + oy], fill=(250, 255, 255, 230))
    for _ in range(140):
        x = r.uniform(0, W); y = r.uniform(0, H); s = r.uniform(1.5, 3.5)
        d.ellipse([x - s, y - s, x + s, y + s], fill=(235, 248, 255, 170))
    d.rectangle([cx - 6, by - 30, cx + 6, by + 6], fill=(90, 90, 100, 255), outline=INK, width=3)
    return img


def make_stove():
    S = 2; W, H = 160 * S, 300 * S
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    pot = [(W * 0.12, H - 4), (W * 0.18, H * 0.62), (W * 0.82, H * 0.62), (W * 0.88, H - 4)]
    d.polygon(pot, fill=(46, 44, 50, 255)); outline(d, pot, 6 * S)
    ch = [(W * 0.4, H * 0.62), (W * 0.42, H * 0.12), (W * 0.58, H * 0.12), (W * 0.6, H * 0.62)]
    d.polygon(ch, fill=(60, 56, 62, 255)); outline(d, ch, 5 * S)
    d.rectangle([W * 0.36, H * 0.08, W * 0.64, H * 0.14], fill=(70, 66, 72, 255), outline=INK, width=4 * S)
    strokes(img, (0, 0, W, H), [(90, 84, 92), (30, 30, 34)], 200, 4, (6 * S, 16 * S), 200, angle=math.pi / 2,
            mask=img.getchannel('A'))
    return shrink(img, S)


def make_flame(seed):
    W, H = 128, 200
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img); r = rng(seed)
    for k, (c, s) in enumerate([((255, 120, 20), 1.0), ((255, 190, 40), 0.7), ((255, 248, 200), 0.38)]):
        w = W * 0.42 * s; h = H * 0.9 * s
        pts = [(W / 2 - w, H - 10), (W / 2 - w * 0.6, H - h * 0.5), (W / 2 + r.uniform(-12, 12), H - h - 10),
               (W / 2 + w * 0.7, H - h * 0.45), (W / 2 + w, H - 10)]
        d.polygon(pts, fill=c + (255,))
    return img.filter(ImageFilter.GaussianBlur(2))


def make_glow(col=(255, 150, 50), S=256):
    y, x = np.mgrid[0:S, 0:S]
    rr = np.hypot(x - S / 2, y - S / 2) / (S / 2)
    a = np.clip(1 - rr, 0, 1) ** 2.2
    g = np.zeros((S, S, 4), np.uint8)
    g[..., 0], g[..., 1], g[..., 2] = col
    g[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(g)


def make_shadow(S=256):
    y, x = np.mgrid[0:S, 0:S]
    rr = np.hypot(x - S / 2, (y - S / 2)) / (S / 2)
    a = np.clip((1 - rr) * 3, 0, 1)
    g = np.zeros((S, S, 4), np.uint8); g[..., 0] = 20; g[..., 1] = 30; g[..., 2] = 80
    g[..., 3] = (a * 150).astype(np.uint8)
    return Image.fromarray(g)


# ---------------------------------------------------------------- boards / props
def wood_board(W, H, seed=3, base=(150, 96, 56)):
    img = Image.new('RGBA', (W, H), base + (255,))
    strokes(img, (0, 0, W, H), [(124, 76, 42), (170, 116, 70), (104, 62, 34), (186, 132, 84)], int(W * H / 300), seed,
            (20, 60), 220, angle=0)
    d = ImageDraw.Draw(img)
    for y in range(0, H, max(40, H // 5)):
        d.line([(0, y), (W, y)], fill=(80, 46, 26, 255), width=4)
    return img


def make_sign(lines, W=900, H=520, seed=3, post=True, sizes=None, colors=None):
    S = 1
    TH = H + (420 if post else 0)
    img = Image.new('RGBA', (W, TH), (0, 0, 0, 0))
    board = wood_board(W - 40, H - 40, seed)
    if post:
        p = wood_board(60, 460, seed + 1, (120, 74, 40))
        img.alpha_composite(p, (W // 2 - 30, H - 60))
        ImageDraw.Draw(img).rectangle([W // 2 - 30, H - 60, W // 2 + 30, TH - 2], outline=INK, width=8)
    img.alpha_composite(board, (20, 20))
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, W - 20, H - 20], outline=INK, width=12)
    n = len(lines); y = 20 + (H - 40) / (n + 1) * 0.5
    for i, ln in enumerate(lines):
        sz = (sizes or [int((H - 60) / (n * 1.25))] * n)[i]
        f = font(sz)
        bb = d.textbbox((0, 0), ln, font=f)
        col = (colors or [(250, 240, 214)] * n)[i]
        tx = (W - (bb[2] - bb[0])) / 2; ty = y
        d.text((tx + 4, ty + 5), ln, font=f, fill=(40, 22, 12, 255))
        d.text((tx, ty), ln, font=f, fill=col + (255,))
        y += sz * 1.22
    return img


def make_newspaper():
    W, H = 860, 1100
    img = Image.new('RGBA', (W, H), (238, 228, 200, 255))
    strokes(img, (0, 0, W, H), [(226, 214, 184), (244, 236, 212)], 900, 9, (20, 50), 160, angle=0)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=10)
    f1 = font(64); f2 = font(150); f3 = font(56)
    d.text((40, 36), 'EL ECO DEL VALLE', font=f1, fill=INK)
    d.line([(40, 120), (W - 40, 120)], fill=INK, width=8)
    d.line([(40, 134), (W - 40, 134)], fill=INK, width=3)
    d.text((40, 160), 'HELADA', font=f2, fill=(170, 30, 30, 255))
    d.text((40, 330), 'ESTA NOCHE:', font=f3, fill=INK)
    d.text((40, 400), '-5°C', font=font(250), fill=(30, 70, 150, 255))
    for i in range(9):
        y = 700 + i * 40
        d.line([(40, y), (W * 0.48, y)], fill=(120, 110, 96, 255), width=12)
        d.line([(W * 0.54, y), (W - 40, y)], fill=(120, 110, 96, 255), width=12)
    # little snowflake icon
    cx, cy = W - 150, 560
    for k in range(6):
        a = k * math.pi / 3
        d.line([(cx, cy), (cx + 90 * math.cos(a), cy + 90 * math.sin(a))], fill=(30, 70, 150, 255), width=12)
    return img


def make_thermo(value, lo=-8, hi=4, marks=(0,), W=300, H=1100, glow=None, label=None):
    """Big painted thermometer with mercury to `value`."""
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    tx0, tx1 = W * 0.36, W * 0.64; ty0, ty1 = 60, H - 220
    d.rounded_rectangle([tx0, ty0 - 40, tx1, ty1 + 40], radius=60, fill=(245, 248, 255, 255), outline=INK, width=12)
    bx = W / 2; by = H - 140
    d.ellipse([bx - 110, by - 110, bx + 110, by + 110], fill=(245, 248, 255, 255), outline=INK, width=12)

    def ty(v): return ty1 - (v - lo) / (hi - lo) * (ty1 - ty0)
    col = (220, 40, 40, 255)
    d.rectangle([bx - 26, ty(value), bx + 26, by], fill=col)
    d.ellipse([bx - 80, by - 80, bx + 80, by + 80], fill=col)
    for v in range(lo, hi + 1):
        y = ty(v); L = 40 if v % 2 == 0 else 22
        d.line([(tx1 - 6, y), (tx1 + L, y)], fill=INK, width=6)
    for v in marks:
        y = ty(v)
        if glow:
            d.rounded_rectangle([0, y - 34, W, y + 34], radius=30, outline=glow + (255,), width=10)
        f = font(64)
        d.text((W - 4, y), f'{v}°', font=f, fill=INK if not glow else glow + (255,), anchor='rm', stroke_width=6,
               stroke_fill=(255, 255, 255, 255))
    if label:
        f = font(90)
        d.text((W / 2, 16), label, font=f, fill=(255, 255, 255, 255), anchor='mt', stroke_width=10, stroke_fill=INK)
    return img


def make_orange_half(kind='juicy', S=700):
    """Cross-section of an orange. kind: juicy | frozen | whole_ice."""
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = S / 2; R = S * 0.44
    if kind == 'whole_ice':
        d.ellipse([c - R, c - R, c + R, c + R], fill=(246, 128, 20, 255), outline=INK, width=14)
        d.ellipse([c - R * 0.6, c - R * 0.7, c - R * 0.05, c - R * 0.2], fill=(255, 200, 90, 255))
        strokes(img, (0, 0, S, S), [(230, 110, 14), (255, 160, 50)], 500, 3, (10, 26), 200, mask=img.getchannel('A'))
        ice = Image.new('RGBA', (S, S), (0, 0, 0, 0)); di = ImageDraw.Draw(ice)
        di.polygon(wobble_poly(c, c, R * 1.18, R * 1.22, 4, 14, 0.06), fill=(200, 236, 255, 55))
        di.line(wobble_poly(c, c, R * 1.18, R * 1.22, 4, 14, 0.06) + [wobble_poly(c, c, R * 1.18, R * 1.22, 4, 14, 0.06)[0]],
                fill=(90, 150, 200, 255), width=10)
        for k in range(8):
            a = -2.4 + k * 0.25
            di.line([(c + math.cos(a) * R * 0.8, c + math.sin(a) * R * 0.8), (c + math.cos(a) * R * 1.05, c + math.sin(a) * R * 1.05)],
                    fill=(255, 255, 255, 240), width=12)
        img.alpha_composite(ice)
        return img
    d.ellipse([c - R, c - R, c + R, c + R], fill=(246, 128, 20, 255))
    d.ellipse([c - R * 0.9, c - R * 0.9, c + R * 0.9, c + R * 0.9], fill=(255, 242, 210, 255))
    flesh = (255, 150, 30) if kind == 'juicy' else (232, 190, 150)
    for k in range(10):
        a0 = k * 36 + 3; a1 = (k + 1) * 36 - 3
        d.pieslice([c - R * 0.82, c - R * 0.82, c + R * 0.82, c + R * 0.82], a0, a1, fill=flesh + (255,))
    if kind == 'juicy':
        r = rng(2)
        for k in range(90):
            a = r.uniform(0, 6.28); rr = R * r.uniform(0.2, 0.75)
            x = c + math.cos(a) * rr; y = c + math.sin(a) * rr; s = r.uniform(6, 14)
            d.ellipse([x - s, y - s * 0.6, x + s, y + s * 0.6], fill=(255, 196, 80, 255))
        d.ellipse([c - R * 0.5, c - R * 0.55, c - R * 0.2, c - R * 0.35], fill=(255, 255, 230, 220))
    else:
        r = rng(5)
        for k in range(60):
            x = c + r.uniform(-R * 0.75, R * 0.75); y = c + r.uniform(-R * 0.75, R * 0.75)
            if math.hypot(x - c, y - c) < R * 0.8:
                s = r.uniform(10, 26)
                pts = [(x + s * math.cos(a), y + s * math.sin(a)) for a in [0, 1.05, 2.1, 3.14, 4.2, 5.25]]
                d.polygon(pts, fill=(235, 250, 255, 230), outline=(120, 170, 210, 255))
                d.line([(x - s, y), (x + s, y)], fill=(255, 255, 255, 255), width=3)
    d.ellipse([c - R * 0.08, c - R * 0.08, c + R * 0.08, c + R * 0.08], fill=(255, 250, 230, 255))
    d.ellipse([c - R, c - R, c + R, c + R], outline=INK, width=14)
    return posterize(img, 6)


def make_knife(W=900, H=200):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    blade = [(W * 0.38, H * 0.3), (W * 0.97, H * 0.45), (W * 0.38, H * 0.72)]
    d.polygon(blade, fill=(210, 220, 232, 255)); outline(d, blade, 10)
    d.line([(W * 0.42, H * 0.42), (W * 0.9, H * 0.46)], fill=(255, 255, 255, 255), width=8)
    d.rounded_rectangle([W * 0.04, H * 0.26, W * 0.4, H * 0.76], radius=30, fill=(110, 60, 34, 255), outline=INK, width=10)
    for x in (0.14, 0.26):
        d.ellipse([W * x - 12, H * 0.5 - 12, W * x + 12, H * 0.5 + 12], fill=(230, 210, 160, 255), outline=INK, width=4)
    return img


def make_pot(W=700, H=700):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    body = [(W * 0.14, H * 0.3), (W * 0.86, H * 0.3), (W * 0.8, H * 0.72), (W * 0.2, H * 0.72)]
    d.polygon(body, fill=(170, 176, 190, 255)); outline(d, body, 12)
    d.ellipse([W * 0.12, H * 0.22, W * 0.88, H * 0.38], fill=(120, 170, 220, 255), outline=INK, width=12)
    for k in range(7):  # bubbles
        x = W * (0.25 + k * 0.08); d.ellipse([x - 18, H * 0.27 - 14, x + 18, H * 0.27 + 14], fill=(235, 248, 255, 255),
                                              outline=(60, 110, 160, 255), width=4)
    d.rectangle([W * 0.02, H * 0.36, W * 0.14, H * 0.42], fill=INK)
    d.rectangle([W * 0.86, H * 0.36, W * 0.98, H * 0.42], fill=INK)
    strokes(img, (0, 0, W, H), [(200, 206, 220), (130, 136, 150)], 300, 2, (10, 30), 200, angle=0.05,
            mask=img.getchannel('A'))
    # burner fire
    for k in range(5):
        x = W * (0.25 + k * 0.125)
        fl = [(x - 40, H * 0.98), (x, H * 0.74), (x + 40, H * 0.98)]
        d.polygon(fl, fill=(255, 130, 20, 255))
        d.polygon([(x - 18, H * 0.98), (x, H * 0.84), (x + 18, H * 0.98)], fill=(255, 230, 120, 255))
    # steam
    for k in range(3):
        x = W * (0.35 + k * 0.15)
        d.line([(x, H * 0.18), (x + 20, H * 0.1), (x - 10, H * 0.02)], fill=(255, 255, 255, 200), width=14, joint='curve')
    return img


def make_heat_particle(S=96):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    g = make_glow((255, 210, 60), S)
    img.alpha_composite(g)
    d.polygon([(S / 2, S * 0.2), (S * 0.72, S * 0.55), (S * 0.55, S * 0.55), (S * 0.6, S * 0.82), (S * 0.3, S * 0.45),
               (S * 0.46, S * 0.45)], fill=(255, 250, 200, 255))
    return img


def make_drop(S=120, ice=False):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    if ice:
        pts = [(S / 2, S * 0.08), (S * 0.86, S * 0.5), (S / 2, S * 0.92), (S * 0.14, S * 0.5)]
        d.polygon(pts, fill=(225, 246, 255, 255)); outline(d, pts, 6, (40, 100, 160, 255))
    else:
        d.polygon([(S / 2, S * 0.05), (S * 0.78, S * 0.6), (S * 0.22, S * 0.6)], fill=(120, 190, 250, 255))
        d.ellipse([S * 0.2, S * 0.38, S * 0.8, S * 0.95], fill=(120, 190, 250, 255), outline=(30, 80, 150, 255), width=5)
        d.ellipse([S * 0.34, S * 0.5, S * 0.46, S * 0.64], fill=(255, 255, 255, 255))
    return img


def make_contract():
    W, H = 700, 900
    img = Image.new('RGBA', (W, H), (246, 238, 214, 255)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=10)
    d.text((W / 2, 70), 'CONTRATO', font=font(96), fill=INK, anchor='mt')
    d.text((W / 2, 190), 'TODO EL INVIERNO', font=font(52), fill=(170, 30, 30, 255), anchor='mt')
    for i in range(8):
        d.line([(60, 300 + i * 46), (W - 60, 300 + i * 46)], fill=(130, 120, 100, 255), width=10)
    d.line([(80, 760), (300, 700), (200, 780), (420, 720)], fill=(20, 40, 140, 255), width=8, joint='curve')
    d.ellipse([W - 220, 680, W - 80, 820], fill=(190, 30, 30, 255), outline=INK, width=6)
    return img


def make_house(W=1200, H=800):
    return wood_board(W, H, 12, (170, 62, 44))


def make_roof(W=1200, H=600):
    img = Image.new('RGBA', (W, H), (70, 58, 60, 255))
    strokes(img, (0, 0, W, H), [(50, 42, 46), (96, 80, 80), (60, 50, 54)], 2000, 4, (20, 50), 220, angle=0)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 60):
        d.line([(0, y), (W, y)], fill=(30, 24, 26, 255), width=6)
    return img


def make_fence(Wm=80, ppm=40, H=120):
    """A long fence strip: Wm metres wide at ppm px/m."""
    W = Wm * ppm
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for y in (int(H * 0.25), int(H * 0.6)):
        d.rectangle([0, y, W, y + 14], fill=(160, 112, 66, 255), outline=INK, width=3)
    for x in range(0, W, int(2.5 * ppm)):
        d.rectangle([x, 0, x + 16, H], fill=(130, 84, 46, 255), outline=INK, width=3)
    return img


def make_steam(S=200):
    img = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for (x, y, r) in [(0.35, 0.6, 0.25), (0.6, 0.45, 0.3), (0.45, 0.3, 0.22)]:
        d.ellipse([S * (x - r), S * (y - r), S * (x + r), S * (y + r)], fill=(255, 255, 255, 240), outline=INK, width=6)
    return img


# ---------------------------------------------------------------- characters
CHAR = {
    'hero': dict(vest=(40, 140, 140), vest2=(28, 110, 112), hat='straw', hair=(140, 80, 40), scarf=(200, 40, 40)),
    'vecino': dict(vest=(214, 160, 40), vest2=(180, 128, 26), hat='bowler', hair=None, chain=True, moustache=True),
    'comprador': dict(vest=(40, 42, 60), vest2=(26, 28, 42), hat='tophat', hair=None, tie=(170, 30, 30)),
}


def make_char(kind, expr='neutral', arms='down', blink=False):
    """Returns RGBA 640x1100 with feet at the bottom center."""
    S = 2
    W, H = 640 * S, 1100 * S
    sp = CHAR[kind]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hx, hy, hr = W / 2, 420 * S, 215 * S
    seed = {'hero': 1, 'vecino': 2, 'comprador': 3}[kind]
    # legs
    for sx in (-1, 1):
        x = W / 2 + sx * 55 * S
        d.line([(x, 860 * S), (x + sx * 10 * S, 1060 * S)], fill=INK, width=16 * S)
        d.ellipse([x + sx * 10 * S - 40 * S + sx * 18 * S, 1040 * S, x + sx * 10 * S + 40 * S + sx * 18 * S, 1090 * S],
                  fill=INK)
    # arms
    ax = {'down': [(-1, (-150, 260)), (1, (150, 260))],
          'up': [(-1, (-190, -170)), (1, (190, -170))],
          'point': [(-1, (-150, 260)), (1, (260, -40))],
          'hip': [(-1, (-150, 160)), (1, (150, 160))],
          'knife': [(-1, (-150, 260)), (1, (240, 40))],
          'shrug': [(-1, (-230, -40)), (1, (230, -40))]}[arms]
    sh_y = 690 * S
    for sx, (dx, dy) in ax:
        x0 = W / 2 + sx * 120 * S
        if arms == 'hip':
            mid = (x0 + sx * 110 * S, sh_y + 60 * S)
            d.line([(x0, sh_y), mid, (x0 + sx * 20 * S, sh_y + 150 * S)], fill=INK, width=14 * S, joint='curve')
            continue
        end = (W / 2 + dx * S, sh_y + dy * S)
        mid = ((x0 + end[0]) / 2 + sx * 30 * S, (sh_y + end[1]) / 2)
        d.line([(x0, sh_y), mid, end], fill=INK, width=14 * S, joint='curve')
        d.ellipse([end[0] - 24 * S, end[1] - 24 * S, end[0] + 24 * S, end[1] + 24 * S], fill=INK)
    # body bean = garment
    body = wobble_poly(W / 2, 745 * S, 150 * S, 140 * S, seed + 10, 40, 0.04)
    d.polygon(body, fill=sp['vest'] + (255,))
    bm = Image.new('L', (W, H), 0); ImageDraw.Draw(bm).polygon(body, fill=255)
    strokes(img, (W / 2 - 160 * S, 600 * S, W / 2 + 160 * S, 900 * S), [sp['vest2'], tuple(min(255, c + 30) for c in sp['vest'])],
            260, seed, (12 * S, 34 * S), 200, mask=bm)
    d = ImageDraw.Draw(img)
    if kind == 'comprador':
        d.polygon([(W / 2 - 50 * S, 612 * S), (W / 2, 700 * S), (W / 2 + 50 * S, 612 * S)], fill=(245, 245, 240, 255))
        d.polygon([(W / 2 - 16 * S, 630 * S), (W / 2 + 16 * S, 630 * S), (W / 2 + 22 * S, 760 * S), (W / 2, 790 * S),
                   (W / 2 - 22 * S, 760 * S)], fill=sp['tie'] + (255,), outline=INK)
        for yb in (720, 780, 840):
            d.ellipse([W / 2 + 60 * S, yb * S, W / 2 + 76 * S, yb * S + 16 * S], fill=(200, 170, 80, 255))
    if sp.get('chain'):
        d.line([(W / 2 - 80 * S, 760 * S), (W / 2, 800 * S), (W / 2 + 80 * S, 760 * S)], fill=(240, 196, 50, 255), width=8 * S,
               joint='curve')
        for yb in (680, 740, 800):
            d.ellipse([W / 2 - 8 * S, yb * S, W / 2 + 8 * S, yb * S + 16 * S], fill=(60, 40, 20, 255))
    if kind == 'hero':
        d.rectangle([W / 2 - 90 * S, 640 * S, W / 2 - 60 * S, 860 * S], fill=(60, 80, 140, 255))
        d.rectangle([W / 2 + 60 * S, 640 * S, W / 2 + 90 * S, 860 * S], fill=(60, 80, 140, 255))
    outline(d, body, 12 * S)
    if sp.get('scarf'):
        sc = [(W / 2 - 110 * S, 610 * S), (W / 2 + 110 * S, 610 * S), (W / 2 + 20 * S, 700 * S), (W / 2 - 20 * S, 700 * S)]
        d.polygon(sc, fill=sp['scarf'] + (255,)); outline(d, sc, 8 * S)
        d.polygon([(W / 2 - 10 * S, 690 * S), (W / 2 + 40 * S, 690 * S), (W / 2 + 30 * S, 760 * S)], fill=sp['scarf'] + (255,),
                  outline=INK)
    # head
    angry = expr == 'angry'
    headcol = (176, 120, 214) if angry else (255, 255, 255)
    head = wobble_poly(hx, hy, hr, hr * 0.97, seed + 20, 56, 0.025)
    d.polygon(head, fill=headcol + (255,))
    hm = Image.new('L', (W, H), 0); ImageDraw.Draw(hm).polygon(head, fill=255)
    strokes(img, (hx - hr, hy - hr, hx + hr, hy + hr), [(230, 232, 240)] if not angry else [(150, 96, 196)], 120, seed, (14 * S, 40 * S),
            90, mask=hm)
    d = ImageDraw.Draw(img)
    outline(d, head, 15 * S)
    if sp['hair']:
        d.polygon([(hx - 40 * S, hy - hr * 0.86), (hx + 60 * S, hy - hr * 0.9), (hx + 10 * S, hy - hr * 0.55),
                   (hx - 10 * S, hy - hr * 0.72), (hx - 50 * S, hy - hr * 0.55)], fill=sp['hair'] + (255,), outline=INK)
    # face
    ey = hy - 10 * S; ex = 72 * S
    brow = {'neutral': (0, 0), 'smug': (-14, 10), 'laugh': (-18, 8), 'angry': (30, 0), 'surprised': (-26, -30),
            'worried': (-26, -8), 'sad': (-22, 0), 'happy': (-10, -10)}[expr]
    for sx in (-1, 1):
        bx = hx + sx * ex
        tilt = brow[0] * S
        by = ey - 70 * S + brow[1] * S
        d.line([(bx - sx * 45 * S, by + (tilt if sx < 0 else -tilt) * 0 + (-tilt if True else 0) * (1 if sx == 1 else 1) * 0),
                (bx + sx * 45 * S, by)], fill=INK, width=1)
        # brows: inner end y offset
        inner = (bx - sx * 45 * S, by + tilt)
        outer = (bx + sx * 45 * S, by - tilt * 0.3)
        d.line([inner, outer], fill=INK, width=20 * S)
        if blink:
            d.line([(bx - 22 * S, ey), (bx + 22 * S, ey)], fill=INK, width=9 * S)
        elif expr in ('surprised', 'worried'):
            rr = 40 * S if expr == 'surprised' else 30 * S
            d.ellipse([bx - rr, ey - rr, bx + rr, ey + rr], fill=(255, 255, 255, 255), outline=INK, width=8 * S)
            d.ellipse([bx - 12 * S, ey - 12 * S, bx + 12 * S, ey + 12 * S], fill=INK)
        elif expr in ('laugh', 'happy'):
            d.arc([bx - 28 * S, ey - 10 * S, bx + 28 * S, ey + 34 * S], 200, 340, fill=INK, width=10 * S)
        elif expr == 'smug':
            d.line([(bx - 26 * S, ey + 4 * S), (bx + 26 * S, ey + 4 * S)], fill=INK, width=10 * S)
            d.ellipse([bx - 10 * S, ey + 4 * S, bx + 10 * S, ey + 20 * S], fill=INK)
        else:
            d.ellipse([bx - 15 * S, ey - 15 * S, bx + 15 * S, ey + 15 * S], fill=INK)
    my = hy + 95 * S
    if sp.get('moustache'):
        d.polygon([(hx - 80 * S, my - 20 * S), (hx, my - 46 * S), (hx + 80 * S, my - 20 * S), (hx + 40 * S, my - 30 * S),
                   (hx, my - 26 * S), (hx - 40 * S, my - 30 * S)], fill=INK)
    if expr == 'angry':
        box = [hx - 80 * S, my - 30 * S, hx + 80 * S, my + 30 * S]
        d.rounded_rectangle(box, radius=10 * S, fill=(255, 255, 255, 255), outline=INK, width=9 * S)
        for i in range(1, 5):
            x = box[0] + i * (box[2] - box[0]) / 5
            d.line([(x, box[1]), (x, box[3])], fill=INK, width=5 * S)
        d.line([(box[0], my), (box[2], my)], fill=INK, width=5 * S)
    elif expr == 'laugh':
        d.chord([hx - 85 * S, my - 50 * S, hx + 85 * S, my + 60 * S], 0, 180, fill=INK)
        d.chord([hx - 50 * S, my + 10 * S, hx + 50 * S, my + 55 * S], 0, 180, fill=(220, 70, 80, 255))
    elif expr in ('smug', 'happy'):
        d.arc([hx - 70 * S, my - 50 * S, hx + 70 * S, my + 20 * S], 20, 160, fill=INK, width=11 * S)
    elif expr == 'surprised':
        d.ellipse([hx - 28 * S, my - 22 * S, hx + 28 * S, my + 36 * S], fill=INK)
    elif expr in ('worried', 'sad'):
        d.arc([hx - 60 * S, my - 6 * S, hx + 60 * S, my + 50 * S], 200, 340, fill=INK, width=11 * S)
    else:
        d.line([(hx - 55 * S, my), (hx + 55 * S, my)], fill=INK, width=11 * S)
    # hats
    if sp['hat'] == 'straw':
        brim = wobble_poly(hx, hy - hr * 0.78, hr * 1.35, hr * 0.22, 5, 40, 0.03)
        d.polygon(brim, fill=(232, 196, 110, 255)); outline(d, brim, 11 * S)
        crown = [(hx - hr * 0.6, hy - hr * 0.82), (hx - hr * 0.5, hy - hr * 1.32), (hx + hr * 0.5, hy - hr * 1.32),
                 (hx + hr * 0.6, hy - hr * 0.82)]
        d.polygon(crown, fill=(240, 206, 120, 255)); outline(d, crown, 11 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 0.98, hx + hr * 0.58, hy - hr * 0.86], fill=(190, 40, 40, 255))
        hm2 = Image.new('L', (W, H), 0); hd2 = ImageDraw.Draw(hm2); hd2.polygon(brim, fill=255); hd2.polygon(crown, fill=255)
        strokes(img, (hx - hr * 1.3, hy - hr * 1.35, hx + hr * 1.3, hy - hr * 0.6), [(200, 160, 80), (250, 220, 150)], 160, 3,
                (10 * S, 24 * S), 160, angle=0.0, mask=hm2)
        d = ImageDraw.Draw(img); outline(d, brim, 11 * S); outline(d, crown, 11 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 0.98, hx + hr * 0.58, hy - hr * 0.86], fill=(190, 40, 40, 255))
    elif sp['hat'] == 'bowler':
        d.ellipse([hx - hr * 1.0, hy - hr * 0.95, hx + hr * 1.0, hy - hr * 0.68], fill=(30, 28, 30, 255), outline=INK,
                  width=8 * S)
        d.chord([hx - hr * 0.68, hy - hr * 1.5, hx + hr * 0.68, hy - hr * 0.5], 180, 360, fill=(36, 34, 38, 255), outline=INK,
                width=8 * S)
        d.arc([hx - hr * 0.5, hy - hr * 1.38, hx - hr * 0.1, hy - hr * 1.0], 200, 260, fill=(110, 110, 120, 255), width=8 * S)
    elif sp['hat'] == 'tophat':
        d.ellipse([hx - hr * 0.95, hy - hr * 0.98, hx + hr * 0.95, hy - hr * 0.72], fill=(24, 22, 26, 255), outline=INK,
                  width=8 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 1.75, hx + hr * 0.58, hy - hr * 0.86], fill=(30, 28, 34, 255), outline=INK,
                    width=8 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 1.06, hx + hr * 0.58, hy - hr * 0.92], fill=(150, 30, 30, 255))
    if expr == 'angry':
        st = make_steam(160 * S)
        img.alpha_composite(st, (int(hx - hr - 150 * S), int(hy - 60 * S)))
        img.alpha_composite(st.transpose(Image.FLIP_LEFT_RIGHT), (int(hx + hr - 10 * S), int(hy - 60 * S)))
    if arms == 'knife':
        k = make_knife(300 * S, 70 * S).rotate(35, expand=True, resample=Image.BICUBIC)
        img.alpha_composite(k, (int(W / 2 + 240 * S - 0.1 * k.width), int(sh_y + 40 * S - 0.75 * k.height)))
    return shrink(img, S)


if __name__ == '__main__':
    import os
    os.makedirs(HERE + '/out', exist_ok=True)
    sheet = Image.new('RGBA', (640 * 6, 1100 * 2), (90, 150, 220, 255))
    for i, e in enumerate(['neutral', 'smug', 'laugh', 'angry', 'surprised', 'worried']):
        sheet.alpha_composite(make_char(['hero', 'vecino', 'comprador'][i % 3], e, ['down', 'hip', 'point', 'up', 'knife', 'shrug'][i]), (640 * i, 0))
    for i, s in enumerate(['normal', 'ice', 'blanket']):
        t = make_tree(s, i + 1, broken=(s == 'ice'))
        sheet.alpha_composite(t.resize((620, 775)), (640 * i, 1150))
    sheet.alpha_composite(make_orange_half('frozen').resize((500, 500)), (640 * 3, 1150))
    sheet.alpha_composite(make_orange_half('juicy').resize((500, 500)), (640 * 4, 1150))
    sheet.alpha_composite(make_thermo(0, glow=(255, 40, 200)).resize((180, 660)), (640 * 5, 1150))
    sheet.alpha_composite(make_stove(), (640 * 5 + 300, 1600))
    sheet.convert('RGB').resize((1920, 1100)).save(HERE + '/out/sheet.jpg', quality=85)
