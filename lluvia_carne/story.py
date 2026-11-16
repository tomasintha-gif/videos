"""'El día que llovió carne' — world, shots and renderer (uses ../naranjos/engine.py)."""
import os, sys, math, json, time, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'naranjos'))
import numpy as np
from PIL import Image, ImageDraw
from multiprocessing import Pool
import assets as A
import cast as C
from engine import Camera, World, billboard, flat, quad, hermite_path, render as eng_render

FPS = 30
RW, RH = 720, 1280
OW, OH = 1080, 1920
WJ = json.load(open(os.path.join(HERE, 'words.json')))
WORDS, TIMES, DUR = WJ['words'], WJ['times'], WJ['duration']
NFR = int(round(DUR * FPS))


def wt(i):
    return TIMES[i][0]


# ------------------------------------------------------------- library
class Lib:
    def __init__(self):
        self.sky = C.make_hills_sky('day')
        g = self.make_ground()
        det = A.make_detail()
        self.world = World(self.sky, g, det, far_col=(110, 150, 60))
        self.tree = [A.make_tree('normal', s, fruit=False) for s in range(1, 5)]
        self.house = A.make_house(); self.roof = A.make_roof()
        self.barn = A.wood_board(1200, 800, 21, (170, 46, 40))
        self.fence = A.make_fence(Wm=80)
        self.shadow = A.make_shadow()
        self.glow = A.make_glow((255, 150, 50)); self.glow_y = A.make_glow((255, 230, 120))
        self.chunks = [C.make_chunk(s, 220) for s in range(8)]
        self.cookie = C.make_cookie()
        self.kettle = C.make_kettle()
        self.bubble_sheep = C.make_bubble(C.make_sheep()); self.bubble_deer = C.make_bubble(C.make_deer())
        self.papers = [C.make_paper(['¡LLUEVE', 'CARNE!'], 'THE KENTUCKY GAZETTE', 1),
                       C.make_paper(['CIELO', 'CARNICERO'], 'DIARIO DEL OESTE', 2),
                       C.make_paper(['¿SE VIENE', 'EL ASADO?'], 'EL ECO DEL VALLE', 3)]
        self.forecast = C.make_forecast()
        self.sign_algas = C.make_easel(C.make_sign('ALGAS', (140, 230, 140)))
        self.sign_pulmon = C.make_easel(C.make_sign('PULMÓN', (255, 160, 170)))
        self.table = A.wood_board(900, 260, 33, (120, 80, 50))
        self.bench = C.make_bench()
        self.exclaim = C.make_exclaim()
        self.chars = {}; self.vult = {}

    def make_ground(self):
        W = 2048
        img = Image.new('RGBA', (W, W), (118, 156, 56, 255))
        A.strokes(img, (0, 0, W, W), [(96, 136, 44), (140, 172, 66), (162, 178, 74), (84, 120, 38)], 60000, 11, (8, 22), 230)
        d = ImageDraw.Draw(img)
        wx = lambda x: (x + 64) * 16
        wz = lambda z: (z + 40) * 16
        box = (wx(-1.5), wz(-40), wx(1.5), wz(88))
        d.rectangle(box, fill=(186, 140, 90, 255))
        A.strokes(img, box, [(200, 156, 100), (170, 124, 80), (214, 170, 116)], 9000, 21, (6, 16), 255, angle=math.pi / 2)
        box = (wx(-9), wz(2), wx(-1.5), wz(13))  # yard
        d.ellipse(box, fill=(176, 136, 86, 255))
        A.strokes(img, box, [(186, 146, 96), (160, 120, 76)], 2500, 31, (6, 16), 230)
        # ploughed field on the right side
        box = (wx(4), wz(-10), wx(30), wz(60))
        for i in range(30):
            x = 4 + i * 0.9
            d.rectangle((wx(x), wz(-10), wx(x + 0.45), wz(60)), fill=(150, 104, 62, 255))
        return A.posterize(img, 5).convert('RGB')

    def char(self, kind, expr='neutral', arms='down', legs='stand', blink=False, frame=0, prop=None):
        k = (kind, expr, arms, legs, blink, frame % 2 if expr == 'chew' else 0, prop)
        if k not in self.chars:
            self.chars[k] = C.make_char(kind, expr, arms, legs, blink, frame, prop)
        return self.chars[k]

    def vulture(self, kind='fly', wing=0, fat=False, eye='normal', vomit=0, napkin=False):
        k = (kind, wing, fat, eye, vomit, napkin)
        if k not in self.vult:
            self.vult[k] = C.make_vulture(kind, wing, fat, eye, vomit, napkin)
        return self.vult[k]


# ------------------------------------------------------------- helpers
def ease(u):
    u = min(1, max(0, u)); return u * u * u * (u * (6 * u - 15) + 10)


def pop(t, t0, dur=0.3):
    u = (t - t0) / dur
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.3 * math.sin(u * math.pi) * (1 - u) * 2 - (1 - u) ** 3


def cam_keys(keys, u):
    P = hermite_path([(k[0], k[1]) for k in keys]); T = hermite_path([(k[0], k[2]) for k in keys])
    F = hermite_path([(k[0], [k[3] if len(k) > 3 else 60]) for k in keys])
    return Camera(P(u), T(u), fov=float(F(u)[0]))


def sched(t, lst):
    v = lst[0][1]
    for t0, val in lst:
        if t >= t0: v = val
    return v


def actor(L, kind, pos, t, plan, h=1.8, phase=0.0, legs='stand', prop=None, bob=0.0):
    expr, arms = sched(t, plan)[:2]
    pr = sched(t, plan)[2] if len(sched(t, plan)) > 2 else prop
    blink = ((t + phase) % 2.9) < 0.08 and expr not in ('laugh', 'yawn', 'chew', 'squint')
    tchg = max([t0 for t0, _ in plan if t0 <= t] + [-9])
    hop = math.exp(-(t - tchg) * 9) * 0.1 if t - tchg < 0.6 else 0
    lean = 0.03 * math.sin((t + phase) * 2.4) + (0.07 * math.exp(-(t - tchg) * 7) if t - tchg < 0.6 else 0)
    if expr == 'laugh':
        lean += 0.05 * math.sin(t * 22)
    tex = L.char(kind, expr, arms, legs, blink, int(t * 8), pr)
    p = np.array(pos, float) + [0, hop * h * 0.3 + bob, 0]
    return [billboard(p, h * (1 + hop * 0.3), tex, lean=lean),
            flat((pos[0], 0, pos[2]), h * 0.55, h * 0.3, L.shadow, opacity=0.8)]


def fall_chunks(L, t, t0, n, area, seed=0, rate=1.0, ground=True, vy=-9.0):
    """Chunks dropping into area=(x0,x1,z0,z1) from t0; landed ones become ground decals."""
    rr = np.random.RandomState(seed)
    it = []
    for i in range(n):
        x = rr.uniform(area[0], area[1]); z = rr.uniform(area[2], area[3])
        ts = t0 + rr.uniform(0, 3.0) / rate
        if t < ts: continue
        y = 14 + vy * (t - ts) - 4.9 * (t - ts) ** 2
        k = i % len(L.chunks)
        if y > 0.1:
            it.append(billboard((x, y, z), 0.6, L.chunks[(k + int(t * 10)) % len(L.chunks)], anchor='center'))
        elif ground:
            it.append(flat((x, 0, z), 0.7, 0.52, L.chunks[k], yaw=rr.uniform(0, 3), y=0.02))
    return it


def static_world(L, cam, scatter=0):
    it = []
    # trees ring
    rr = np.random.RandomState(5)
    for i in range(46):
        a = rr.uniform(0, 2 * math.pi); r = rr.uniform(16, 50)
        x, z = math.cos(a) * r, 10 + math.sin(a) * r
        if abs(x) < 3: continue
        v = np.array([x, 2, z]) - cam.pos
        if v @ cam.f < -3: continue
        it.append(billboard((x, 0, z), rr.uniform(4.5, 6.5), L.tree[i % 4]))
        it.append(flat((x + 1.2, 0, z + 1), 5, 3, L.shadow, yaw=0.5))
    # house
    it += box(L, -7, 11, 7, 3.4, 5, L.house, L.roof)
    it += box(L, 9, 22, 9, 5, 7, L.barn, L.roof)
    for xf in (-2.2, 2.2):
        it.append(quad([(xf, 1.2, -20), (xf, 1.2, 60), (xf, 0, 60), (xf, 0, -20)], L.fence))
    # meat scattered on the ground (already fallen)
    if scatter:
        rs = np.random.RandomState(9)
        for i in range(scatter):
            x = rs.uniform(-14, 14); z = rs.uniform(-4, 30)
            if (np.array([x, 0, z]) - cam.pos) @ cam.f < 0: continue
            it.append(flat((x, 0, z), 0.7, 0.52, L.chunks[i % 8], yaw=rs.uniform(0, 3), y=0.02))
    return it


def box(L, cx, cz, w, h, d, wall, roof):
    x0, x1 = cx - w / 2, cx + w / 2; z0, z1 = cz - d / 2, cz + d / 2
    it = [quad(q, wall) for q in ([(x0, h, z0), (x1, h, z0), (x1, 0, z0), (x0, 0, z0)],
                                  [(x1, h, z1), (x0, h, z1), (x0, 0, z1), (x1, 0, z1)],
                                  [(x0, h, z1), (x0, h, z0), (x0, 0, z0), (x0, 0, z1)],
                                  [(x1, h, z0), (x1, h, z1), (x1, 0, z1), (x1, 0, z0)])]
    ry = h + 2.0
    it.append(quad([(x0 - 0.5, ry, cz), (x1 + 0.5, ry, cz), (x1 + 0.5, h - 0.3, z1 + 0.6), (x0 - 0.5, h - 0.3, z1 + 0.6)], roof, bias=-0.5))
    it.append(quad([(x1 + 0.5, ry, cz), (x0 - 0.5, ry, cz), (x0 - 0.5, h - 0.3, z0 - 0.6), (x1 + 0.5, h - 0.3, z0 - 0.6)], roof, bias=-0.5))
    # gable triangles approximated by a quad with transparent top corners is skipped; roof overhang hides it
    return it


def flock(L, t, center, n, radius, seed=1, vomit_at=None, scale=2.2, flap=7):
    it = []
    rr = np.random.RandomState(seed)
    for i in range(n):
        a = rr.uniform(0, 6.28) + t * 0.35 * (1 if i % 2 else -1) * rr.uniform(0.6, 1.2)
        r = radius * rr.uniform(0.5, 1.0)
        p = np.array(center, float) + [math.cos(a) * r, rr.uniform(-3, 3), math.sin(a) * r * 0.6]
        wing = int(t * flap + i) % 2
        vom = vomit_at is not None and t > vomit_at[i % len(vomit_at)]
        tex = L.vulture('fly', wing, eye='scared' if vom else 'normal', vomit=1 if vom else 0)
        it.append(billboard(p, scale, tex, anchor='center', flip=bool(i % 2)))
        if vom:
            dt = t - vomit_at[i % len(vomit_at)]
            for k in range(5):
                tt = dt - k * 0.12
                if tt <= 0: continue
                q = p + [0, -4.9 * tt * tt - 1.0 * tt, 0]
                it.append(billboard(q, 0.5, L.chunks[(i + k) % 8], anchor='center'))
    return it


# ------------------------------------------------------------- shots
# signature f(L, t, d) -> (cam, items, grade, dof)
def grade_blue(f):
    g = f * np.array([0.62, 0.78, 1.08], np.float32) + np.array([8, 16, 40], np.float32)
    return g


def sh_hook(L, t, d):
    u = t / d
    c = cam_keys([(0, (0.4, 0.8, -2), (0.2, 9, 14), 72), (0.6, (0.3, 1.0, -1), (0, 5, 14), 66),
                  (1, (0.2, 1.3, 0.5), (-1.5, 1.6, 8), 60)], u)
    it = static_world(L, c, scatter=int(40 * u))
    it += fall_chunks(L, t, -1.0, 110, (-6, 6, 3, 16), seed=1, rate=0.55)
    # a big chunk slaps near the lens on "carne"
    tc = wt(13) - 0.15
    if t > tc - 0.35:
        y = max(0.06, 2.6 - 22 * (t - tc + 0.35) ** 2 * 2)
        it.append(billboard((0.0, y, 2.4), 0.55, L.chunks[3], anchor='center'))
    return c, it, None, None


def sh_calm(L, t, d):
    c = cam_keys([(0, (5, 2.6, -3), (-3, 1.4, 8), 60), (1, (2.5, 2.2, -2.5), (-3, 1.4, 8), 58)], t / d)
    it = static_world(L, c)
    it += actor(L, 'crouch', (-2.2, 0, 6.0), t, [(0, ('happy', 'stir'))], phase=0.4)
    it.append(billboard((-3.1, 0, 5.5), 1.3, L.kettle))
    return c, it, None, None


def sh_crouch(L, t, d, t0):
    tc, tk = wt(29) - t0, wt(33) - t0
    c = cam_keys([(0, (-0.5, 1.6, 0.8), (-2.4, 1.4, 6), 58), (0.7, (-1.2, 1.55, 2.6), (-2.4, 1.5, 6), 52),
                  (1, (-1.8, 1.65, 3.6), (-2.3, 1.65, 6), 46)], t / d)
    it = static_world(L, c)
    it.append(billboard((-3.0, 0, 5.4), 1.3, L.kettle))
    it += actor(L, 'crouch', (-2.2, 0, 6.0), t, [(0, ('happy', 'stir')), (tc + 0.2, ('worried', 'stir')), (tk, ('surprised', 'up'))])
    it += fall_chunks(L, t, tc - 0.6, 60, (-5, 2, 4, 12), seed=2, rate=1.0)
    return c, it, None, (6.5, 2.0)


def sh_field(L, t, d, t0):
    tg = wt(47) - t0
    u = t / d
    if t < tg - 0.4:
        c = cam_keys([(0, (-2, 3, -4), (0, 0, 10), 60), (1, (0, 26, -8), (0, 0, 14), 56)], t / (tg - 0.4))
    else:
        v = (t - (tg - 0.4)) / max(0.1, d - (tg - 0.4))
        c = cam_keys([(0, (0.6, 0.5, 1.0), (0, 0.1, 3.2), 50), (1, (0.45, 0.42, 1.8), (0, 0.1, 3.2), 46)], v)
    it = static_world(L, c, scatter=260)
    it.append(flat((0.15, 0, 3.2), 0.42, 0.32, L.chunks[2], y=0.03))
    k = pop(t, tg - 0.1)
    if k > 0:
        it.append(flat((-0.35, 0, 3.15), 0.3 * k, 0.3 * k, L.cookie, y=0.03))
        it.append(billboard((-0.35, 0.02, 3.3), 0.26 * k, L.cookie))
    return c, it, None, (4.0, 1.5) if t > tg - 0.4 else None


def sh_run(L, t, d):
    z = 14 - 2.8 * t
    c = cam_keys([(0, (0.2, 1.0, z - 5.5), (0.4, 1.0, z), 62), (1, (-0.2, 1.1, z - 5.0), (0.4, 1.0, z), 60)], t / d)
    it = static_world(L, c, scatter=200)
    ph = int(t * 8) % 2
    for kind, x, off in (('silas', -0.3, 0.0), ('ezra', 1.2, 0.6)):
        legs = 'runA' if (ph + (1 if off else 0)) % 2 else 'runB'
        it += actor(L, kind, (x, 0, z + off), t, [(0, ('surprised', legs))], legs=legs, bob=0.06 * abs(math.sin(t * 12 + off)))
    return c, it, None, None


TASTE = ((-0.6, 0, 9.0), (0.8, 0, 9.3))


def sh_taste(L, t, d, t0):
    tp = wt(62) - t0
    c = cam_keys([(0, (0.1, 1.5, 4.8), (0.1, 1.4, 9.1), 52), (1, (0.1, 1.5, 6.0), (0.1, 1.45, 9.1), 50)], t / d)
    it = static_world(L, c, scatter=200)
    it += actor(L, 'silas', TASTE[0], t, [(0, ('think', 'hold', 'chunk')), (tp - 0.25, ('happy', 'eat', 'chunk')), (tp + 0.25, ('chew', 'eat', None))])
    it += actor(L, 'ezra', TASTE[1], t, [(0, ('worried', 'hold', 'chunk')), (tp - 0.15, ('squint', 'eat', 'chunk')), (tp + 0.35, ('chew', 'eat', None))], phase=1)
    return c, it, None, (11, 2.2)


def sh_cu(L, t, d, kind, pos, plan, bubble, side):
    c = cam_keys([(0, (pos[0] + side * 0.25, 1.75, pos[2] - 2.4), (pos[0], 1.55, pos[2]), 46),
                  (1, (pos[0] + side * 0.1, 1.7, pos[2] - 1.8), (pos[0], 1.55, pos[2]), 44)], t / d)
    it = static_world(L, c, scatter=200)
    it += actor(L, kind, pos, t, plan)
    k = pop(t, 0.15)
    if k > 0:
        it.append(billboard(np.array(pos) + c.r * (-0.22 * side) + [0, 2.2, -0.1], 0.5 * k, bubble, anchor='center'))
    return c, it, None, (pos[2] + 3 - c.pos[2], 2.5)


def sh_papers(L, t, d):
    c = Camera((0.2 + 0.2 * math.sin(t), 2.0, 0), (0, 4.0, 10), fov=60)
    it = static_world(L, c, scatter=200)
    for i, p in enumerate(L.papers):
        ts = 0.1 + i * 0.5
        if t < ts: continue
        u = t - ts
        z = 9 - u * 5.5; x = (-1.0, 1.1, 0)[i] * (1 - u * 0.25); y = 3.0 + (0.4, -0.3, 0.6)[i] + 0.2 * math.sin(u * 5)
        it.append(billboard((x, y, max(1.4, z)), 1.2, p, anchor='center', lean=0.15 * math.sin(u * 4 + i)))
    return c, it, None, None


def sh_forecast(L, t, d, t0):
    a = -0.45 + 0.6 * t / d
    tgt = np.array([0, 1.8, 10])
    c = Camera(tgt + [math.sin(a) * 4.4, 0.1, -math.cos(a) * 4.4], tgt + [0, -0.2, 0], fov=52)
    it = static_world(L, c, scatter=200)
    it.append(billboard((0, 0.9, 10), 1.5, L.forecast))
    it.append(quad([(-0.1, 0.95, 10.05), (0.1, 0.95, 10.05), (0.1, 0, 10.05), (-0.1, 0, 10.05)], L.table))
    return c, it, None, (8, 2.0)


def sh_experts(L, t, d, t0):
    ta, tp = wt(91) - t0, wt(95) - t0
    c = cam_keys([(0, (0.1, 1.7, 9.0), (0.1, 1.5, 14), 56), (1, (0.1, 1.65, 10.0), (0.1, 1.5, 14), 52)], t / d)
    it = static_world(L, c, scatter=200)
    it += actor(L, 'expert1', (0.75, 0, 14.0), t, [(0, ('think', 'magnify')), (ta - 0.2, ('smug', 'point'))])
    it += actor(L, 'expert2', (-0.6, 0, 14.0), t, [(0, ('neutral', 'down')), (tp - 0.3, ('happy', 'point'))], phase=0.7)
    k = pop(t, ta - 0.15)
    if k > 0:
        it.append(billboard((0.75, 0, 15.6), 2.0 * k, L.sign_algas))
    k = pop(t, tp - 0.15)
    if k > 0:
        it.append(billboard((-0.6, 0, 15.3), 2.0 * k, L.sign_pulmon))
    return c, it, None, (9, 2.0)


DOC = (0.4, 0, 12.0)


def sh_doctor(L, t, d, t0):
    tm = wt(101) - t0
    if t < tm:
        c = cam_keys([(0, (0.1, 1.6, 8.2), (0.4, 1.5, 12), 52), (1, (0.25, 1.62, 9.6), (0.4, 1.6, 12), 46)], t / tm)
    else:
        v = ease((t - tm) / min(1.4, d - tm))
        c = Camera((0.25, 1.62 - 0.6 * v, 9.6 - 0.9 * v), (0.4, 1.75 + 0.35 * v, 12), fov=46 + 12 * v)
    it = static_world(L, c, scatter=200)
    it += actor(L, 'doctor', DOC, t, [(0, ('think', 'bag')), (tm, ('surprised', 'bag')), (tm + 1.0, ('think', 'point'))])
    return c, it, None, (5, 2.0) if t < tm else None


def sh_reveal(L, t, d, t0):
    tc = wt(117) - t0
    c = Camera((0, 1.6, 6), (0.4 + 2 * math.sin(t * 0.4), 14, 18), fov=62, roll=0.06 * math.sin(t * 1.3))
    it = static_world(L, c, scatter=200)
    n = 3 + int(9 * min(1, t / tc))
    it += flock(L, t, (0, 16, 20), n, 7, seed=3, scale=3.0)
    k = pop(t, tc)
    if k > 0:  # one vulture swoops close
        it.append(billboard(c.pos + c.f * 3.0 + c.u * 0.2, 1.4 * k, L.vulture('fly', int(t * 7) % 2, eye='happy'), anchor='center'))
    return c, it, None, None


def sh_fat(L, t, d, t0):
    tt = wt(128) - t0
    tgt = np.array([5.0, 0.9, 12.0])
    a = 0.6 + 0.35 * t / d
    c = Camera(tgt + [-math.sin(a) * 4.2, 0.6, -math.cos(a) * 4.2], tgt, fov=50)
    it = static_world(L, c, scatter=200)
    hopy = max(0, math.sin(t * 9)) * 0.25 if t > tt - 1.2 else 0
    wing = int(t * 14) % 2 if t > tt - 1.2 else 0
    it.append(billboard((5.0, hopy, 12.0), 2.0, L.vulture('fly' if t > tt - 1.2 else 'perch', wing, fat=True,
                                                           eye='scared' if t > tt else 'happy')))
    it.append(flat((5.0, 0, 12.0), 1.6, 0.6, L.shadow))
    for i in range(6):
        it.append(flat((4.4 + i * 0.25, 0, 11.6 + (i % 3) * 0.3), 0.4, 0.3, L.chunks[i], y=0.03))
    it.append(billboard((7.2, 0, 13.5), 1.3, L.vulture('perch', 0, fat=True, eye='happy', napkin=True)))
    return c, it, grade_blue, (7, 1.6)


def sh_scare(L, t, d, t0):
    ts, tv = wt(132) - t0, wt(133) - t0
    p = np.array([0.0, 22.0 + max(0, t - tv - 0.6) * 3.0, 20.0 + t * 1.5])
    c = Camera(p + [-1.0, 0.3, -5.2], p + [0, -0.2, 0], fov=50, roll=0.05 * math.sin(t * 2))
    it = []
    fat = t < tv + 0.5
    it.append(billboard(p, 2.6, L.vulture('fly', int(t * (9 if fat else 6)) % 2, fat=fat,
                                          eye='scared' if t > ts else 'normal', vomit=1 if tv < t < tv + 1.2 else 0), anchor='center'))
    k = pop(t, ts)
    if 0 < k and t < tv + 0.6:
        it.append(billboard(p + c.r * -0.2 + [0, 1.35, 0], 0.8 * k, L.exclaim, anchor='center'))
    if t > tv:
        for i in range(10):
            tt = t - tv - i * 0.07
            if tt <= 0: continue
            q = p + c.r * (-1.0) + [0.3 * math.sin(i), 0.5 - 4.9 * tt * tt - 2 * tt, 0.2]
            it.append(billboard(q, 0.45, L.chunks[i % 8], anchor='center'))
    return c, it, grade_blue, None


def sh_chain(L, t, d, t0):
    c = Camera((0, 26, 3.0 + t * 0.8), (0, 25.5, 20), fov=62)
    it = []
    vom = [0.4 + i * 0.32 for i in range(7)]
    rr = np.random.RandomState(2)
    for i in range(7):
        p = np.array([-6 + i * 2.0, 26 + rr.uniform(-1, 1), 17 + rr.uniform(-2, 2)])
        on = t > vom[i]
        it.append(billboard(p, 2.2, L.vulture('fly', int(t * 7 + i) % 2, eye='scared' if on else 'normal', vomit=1 if on else 0),
                            anchor='center'))
        if on:
            for k in range(5):
                tt = t - vom[i] - k * 0.1
                if tt <= 0: continue
                it.append(billboard(p + [-0.7, 0.4 - 4.9 * tt * tt, 0], 0.4, L.chunks[(i + k) % 8], anchor='center'))
    return c, it, grade_blue, None


def sh_yawn(L, t, d, t0):
    ty = [wt(150) - t0, wt(152) - t0, wt(152) - t0 + 0.4]
    c = cam_keys([(0, (-5.0, 1.1, 2.8), (-5.0, 0.95, 7), 52), (1, (-5.0, 1.05, 3.4), (-5.0, 0.95, 7), 50)], t / d)
    it = static_world(L, c)
    it.append(billboard((-5.0, 0, 7.25), 0.8, L.bench, w=3.0))
    for i, kind in enumerate(('silas', 'crouch', 'ezra')):
        x = -5.95 + i * 0.95
        plan = [(0, ('neutral', 'lap')), (ty[i], ('yawn', 'yawn')), (ty[i] + 0.9, ('neutral', 'lap'))]
        it += actor(L, kind, (x, 0.05, 7.0), t, plan, h=1.45, phase=i * 0.7, legs='sit')
    return c, it, grade_blue, (6, 1.8)


def sh_flock(L, t, d, t0):
    c = cam_keys([(0, (-12, 6, -14), (0, 8, 14), 62), (1, (-16, 10, -20), (0, 10, 14), 60)], t / d)
    it = static_world(L, c, scatter=300)
    vom = [0.3 + i * 0.07 for i in range(14)]
    it += flock(L, t, (0, 26, 14), 14, 12, seed=7, vomit_at=vom, scale=2.6)
    it += fall_chunks(L, t, 0.6, 90, (-10, 10, 2, 26), seed=5, rate=2.5)
    return c, it, None, None


def sh_twist(L, t, d, t0):
    c = cam_keys([(0, (0.1, 1.5, 4.6), (0.1, 1.4, 9.1), 54), (1, (-0.1, 1.55, 6.4), (-0.2, 1.5, 9.1), 48)], t / d)
    it = static_world(L, c, scatter=200)
    it += actor(L, 'silas', TASTE[0], t, [(0, ('chew', 'eat'))])
    it += actor(L, 'ezra', TASTE[1], t, [(0, ('chew', 'eat'))], phase=1)
    return c, it, None, (11, 2.2)


def sh_final(L, t, d, t0):
    tb = wt(181) - t0
    roll = 0.06 * ease(t / d)
    p = np.array(TASTE[0])
    c = Camera(p + [0.15, 1.62, -2.6 + 1.0 * ease(t / d)], p + [0, 1.55, 0], fov=46, roll=roll)
    it = static_world(L, c, scatter=200)
    it += actor(L, 'silas', TASTE[0], t, [(0, ('chew', 'eat')), (tb - 0.08, ('sick', 'cover'))])
    # vulture lands on the fence behind, napkin on
    tl = tb - 1.6
    if t > tl:
        u = min(1, (t - tl) / 0.9)
        q = p + c.r * 0.55 + [0, 0.9 + 4 * (1 - ease(u)), 2.2]
        it.append(billboard(q, 1.4, L.vulture('perch' if u >= 1 else 'fly', int(t * 8) % 2, eye='happy', napkin=True)))
    return c, it, None, (11.8, 2.4)


# shot table: (start_word, func, needs_t0)
SHOTS = [(0, sh_hook, 0), (14, sh_calm, 0), (18, sh_crouch, 1), (34, sh_field, 1), (48, sh_run, 0), (52, sh_taste, 1),
         (63, lambda L, t, d: sh_cu(L, t, d, 'silas', TASTE[0], [(0, ('chew', 'eat')), (0.6, ('happy', 'eat'))], L.bubble_sheep, 1), 0),
         (68, lambda L, t, d: sh_cu(L, t, d, 'ezra', TASTE[1], [(0, ('chew', 'eat')), (0.4, ('squint', 'hold'))], L.bubble_deer, -1), 0),
         (71, sh_papers, 0), (79, sh_forecast, 1), (86, sh_experts, 1), (96, sh_doctor, 1), (112, sh_reveal, 1),
         (119, sh_fat, 1), (129, sh_scare, 1), (139, sh_chain, 1), (147, sh_yawn, 1), (156, sh_flock, 1), (166, sh_twist, 1),
         (175, sh_final, 1)]
STARTS = [0.0] + [max(0, wt(w) - 0.1) for w, _, _ in SHOTS[1:]]
ENDS = STARTS[1:] + [DUR]
FLASH_AT = [STARTS[13]]   # into the explanation
XF = 0.12

L = None


def init():
    global L
    L = Lib()


def shot_frame(i, T):
    w, f, need = SHOTS[i]
    d = ENDS[i] - STARTS[i]; t = T - STARTS[i]
    out = f(L, t, d, STARTS[i]) if need else f(L, t, d)
    c, it, grade, dof = out
    fog = (170, 200, 230)
    return eng_render(c, L.world, it, fog, grade=grade, dof=dof)


def frame_at(T):
    i = max(j for j in range(len(STARTS)) if STARTS[j] <= T)
    fr = shot_frame(i, T)
    if i + 1 < len(STARTS) and STARTS[i + 1] - T < XF:
        a = 1 - (STARTS[i + 1] - T) / XF
        fr = fr * (1 - a * 0.5) + shot_frame(i + 1, T) * (a * 0.5)
    if i > 0 and T - STARTS[i] < XF:
        a = (T - STARTS[i]) / XF
        fr = shot_frame(i - 1, T) * (0.5 - 0.5 * a) + fr * (0.5 + 0.5 * a)
    for fa in FLASH_AT:
        if 0 <= T - fa < 0.2:
            k = 1 - (T - fa) / 0.2
            fr = fr * (1 - k) + 255 * k
    # vignette
    return np.clip(fr * VIG, 0, 255)


yy, xx = np.mgrid[0:RH, 0:RW]
VIG = (1 - 0.28 * (((xx - RW / 2) / (RW / 2)) ** 2 + ((yy - RH / 2) / (RH / 2)) ** 2) ** 1.5)[..., None].astype(np.float32)
GRAIN = None


def finish(fr):
    global GRAIN
    img = Image.fromarray(fr.astype(np.uint8)).resize((OW, OH), Image.BICUBIC)
    if GRAIN is None:
        g = np.random.RandomState(0).normal(0, 4, (OH // 4, OW // 4)).astype(np.float32)
        GRAIN = np.asarray(Image.fromarray(g).resize((OW, OH), Image.BICUBIC))[..., None]
    return Image.fromarray(np.clip(np.asarray(img, np.float32) + GRAIN, 0, 255).astype(np.uint8))


def work(a):
    f0, f1, outdir = a
    for f in range(f0, f1):
        p = os.path.join(outdir, f'f{f:05d}.jpg')
        if os.environ.get('RESUME') and os.path.exists(p):
            continue
        finish(frame_at(f / FPS)).save(p, quality=93)
    return f1 - f0


def stills(times, out):
    init()
    ims = [finish(frame_at(T)).resize((240, 427)) for T in times]
    cols = 10; rows = (len(ims) + cols - 1) // cols
    s = Image.new('RGB', (240 * cols, 427 * rows), (0, 0, 0))
    for k, im in enumerate(ims):
        s.paste(im, ((k % cols) * 240, (k // cols) * 427))
        ImageDraw.Draw(s).text(((k % cols) * 240 + 6, (k // cols) * 427 + 4), f'{times[k]:.1f}s', fill=(255, 255, 0))
    s.save(out, quality=88)


if __name__ == '__main__':
    if sys.argv[1] == 'stills':
        ts = [(STARTS[i] + ENDS[i]) / 2 for i in range(len(STARTS))]
        if len(sys.argv) > 2:
            ts = [float(x) for x in sys.argv[2].split(',')]
        stills(ts, os.path.join(HERE, 'out', 'stills.jpg'))
    elif sys.argv[1] == 'frames':
        outdir = os.path.join(HERE, 'out', 'frames'); os.makedirs(outdir, exist_ok=True)
        chunks = [(f, min(NFR, f + 12), outdir) for f in range(0, NFR, 12)]
        t0 = time.time(); done = 0
        with Pool(os.cpu_count(), initializer=init) as p:
            for n in p.imap_unordered(work, chunks):
                done += n
                if done % 120 < 12:
                    print(f'{done}/{NFR} {time.time() - t0:.0f}s', flush=True)
        print('rendered', flush=True)
