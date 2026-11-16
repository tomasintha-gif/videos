"""Shot list for 'Naranjos en la helada'. Each shot returns camera + items for local time t."""
import math, re, json
import numpy as np
from engine import Camera, billboard, flat, quad, hermite_path
import world as Wd

SCRIPT = """| Regó sus naranjos en plena helada. | Verás, un comprador iba a elegir una sola finca para todo el invierno. | Y esa noche, el pronóstico marcaba @m5 cinco bajo cero. | El vecino prendió estufas entre las filas y tapó sus árboles con @mantas mantas. | Él abrió los aspersores, y los dejó toda la noche. | ¿Vas a vender paletas heladas?, se rió el vecino. @dos Mañana te compro el campo por dos pesos. | Al amanecer, su campo era una cueva de hielo. | Las ramas crujían, @parte una se partió, y las @nar naranjas colgaban atrapadas en vidrio. | El comprador ni lo miró. | Fue directo a lo del vecino y @corta cortó una naranja. @c1 Cristales de hielo por dentro. @c2 Luego otra. @c3 Luego todas, crujiendo como granizado. | Volvió, @rompe rompió el hielo de una de las suyas, y @apoya apoyó el cuchillo. | Verás, cuando el agua se congela, @calor suelta calor. | Mientras siga cayendo agua y congelándose, la fruta queda trabada en @cero cero grados, | como una olla que no pasa de @cien cien, por más fuego que le pongas. | Y una naranja recién se congela por debajo de los @dos2 dos bajo cero. | El cuchillo salió chorreando jugo. | El vecino se quedó con sus mantas, | y el comprador @firma firmó todo el invierno con el único loco que"""


def parse():
    words = []; shots = []; events = {}
    pend = []
    for tok in SCRIPT.split():
        if tok == '|':
            shots.append(len(words)); continue
        if tok.startswith('@'):
            pend.append(tok[1:]); continue
        for e in pend:
            events[e] = len(words)
        pend = []
        words.append(tok)
    return words, shots, events


WORDS, SHOT_START, EVENTS = parse()


def estimate_times(words, total=None):
    """Fallback word timings (start, end) when no transcript is available."""
    t = 0.15; out = []
    for w in words:
        letters = len(re.sub(r'[^\wáéíóúñü]', '', w))
        d = 0.07 + 0.045 * letters
        out.append((t, t + d)); t += d
        if w.endswith((',', ';')): t += 0.18
        if w.endswith(('.', '?', '!')): t += 0.32
    return out


# ------------------------------------------------------------- helpers
def ease(u):
    u = min(1, max(0, u)); return u * u * (3 - 2 * u)


def pop(t, t0, dur=0.35):
    """0 before t0, overshoot to 1."""
    u = (t - t0) / dur
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.35 * math.sin(u * math.pi) * (1 - u) * 2 - (1 - u) ** 3


def cam_path(keys, fov=62, roll_keys=None):
    P = hermite_path([(k[0], k[1]) for k in keys]); T = hermite_path([(k[0], k[2]) for k in keys])
    F = hermite_path([(k[0], [k[3] if len(k) > 3 else fov]) for k in keys])

    def c(u):
        return Camera(P(u), T(u), fov=float(F(u)[0]))
    return c


def sched(t, lst):
    """lst = [(t0, value), ...] -> active value."""
    v = lst[0][1]
    for t0, val in lst:
        if t >= t0: v = val
    return v


def char(L, kind, pos, t, plan, h=1.9, lean_amp=0.035, phase=0.0, scale=1.0, face=None, flip=False):
    expr, arms = sched(t, plan)
    # blink every ~2.7s
    blink = ((t + phase) % 2.7) < 0.09 and expr not in ('laugh', 'angry')
    # little hop on expression change
    tchg = max([t0 for t0, _ in plan if t0 <= t] + [-9])
    hop = math.exp(-(t - tchg) * 9) * 0.12 if t - tchg < 0.6 else 0
    lean = lean_amp * math.sin((t + phase) * 2.6) + (0.08 * math.exp(-(t - tchg) * 7) if t - tchg < 0.6 else 0)
    tex = L.char(kind, expr, arms, blink)
    p = np.array(pos, float)
    b = billboard(p + [0, hop * h * 0.3, 0], h * scale * (1 + hop * 0.4), tex, lean=lean, face=face, flip=flip)
    b['post'] = True
    return b


def fog(sky):
    return {'day': (156, 196, 236), 'night': (26, 40, 86), 'dawn': (226, 208, 214), 'dusk': (236, 180, 160)}[sky]


class Shot:
    def __init__(self, sky, grade, tint=None):
        self.sky = sky; self.grade = grade; self.tint = tint


# ------------------------------------------------------------- shots
# each: f(L, t, d, ev) -> (cam, items, emissive, sky_key, fog, grade, tint)
# ev: dict event -> local time

def s_hook(L, t, d, ev):
    c = cam_path([(0, (-8, 0.35, 5.0), (-8, 1.2, 20)), (0.55, (-8, 0.9, 11.0), (-8, 1.8, 22)),
                  (1.0, (-9.0, 3.4, 12.0), (-7.5, 1.6, 22), 70)], fov=74)(t / d)
    em = []
    on = t > 0.25
    items = Wd.orchard(L, c, 'normal', 'blanket', t, sprays=on, stoves=True, emissive=em)
    items.append(char(L, 'hero', (-7.6, 0, 16.0), t, [(0, ('neutral', 'point')), (0.3, ('happy', 'up'))], h=1.9))
    if on:
        items.append(billboard((-8, 0.0, 17.5), 2.6, L.spray[int(t * 14) % 3], w=4.6))
    return c, items, em, 'night', fog('night'), Wd.grade_night, None


def s_buyer(L, t, d, ev):
    c = cam_path([(0, (2, 46, -24), (0, 0, 14), 55), (0.45, (1.5, 9, -2), (0, 1, 10), 60),
                  (1.0, (0.4, 1.7, 6.0), (0, 1.55, 9.0), 55)])(t / d)
    items = Wd.orchard(L, c, 'normal', 'normal', t)
    items.append(char(L, 'comprador', (0, 0, 9.0), t, [(0, ('smug', 'hip')), (d * 0.7, ('neutral', 'point'))]))
    items.append(billboard((1.45, 0, 9.6), 2.2, L.sign_buyer))
    items.append(flat((0.7, 0, 9.9), 2.2, 1.2, L.shadow, yaw=0.5))
    return c, items, [], 'day', fog('day'), None, None


def s_forecast(L, t, d, ev):
    u = t / d
    c = cam_path([(0, (-0.2, 1.4, 4.0), (-2.2, 1.4, 8.0), 60), (0.6, (-0.6, 1.4, 6.3), (-2.3, 1.3, 8.2), 55),
                  (1.0, (-1.2, 1.25, 7.1), (-2.3, 1.15, 8.4), 50)])(u)
    items = Wd.orchard(L, c, 'normal', 'normal', t)
    items.append(billboard((-2.2, 0.55, 8.2), 1.25, L.news, face=math.pi / 2 + 0.0))
    m = pop(t, ev.get('m5', d * 0.6))
    if m > 0:
        items.append(billboard((-2.15, 0.3, 9.6), 1.9 * m, L.thermo_m5, face=math.pi / 2))
        items.append(billboard((-2.12, 1.2, 9.3), 1.4 * m, L.glow_c, w=1.4 * m, mode='add', opacity=0.5, face=math.pi / 2))
    return c, items, [], 'dawn', fog('dusk'), Wd.grade_dusk, None


def s_stoves(L, t, d, ev):
    c = cam_path([(0, (6.9, 0.5, 2), (7.0, 1.0, 20), 72), (0.6, (7.0, 0.8, 9), (7.1, 1.2, 22), 68),
                  (1.0, (7.1, 1.45, 13.6), (7.2, 1.45, 17), 56)])(t / d)
    em = []
    items = Wd.orchard(L, c, 'normal', 'blanket', t, stoves=True, emissive=em)
    tm = ev.get('mantas', d * 0.8)
    items.append(char(L, 'vecino', (7.2, 0, 17.0), t, [(0, ('smug', 'hip')), (tm, ('laugh', 'up'))]))
    em.append(billboard((7.2, -0.5, 17.4), 3.0, L.glow, w=4, mode='add', opacity=0.35))
    return c, items, em, 'night', fog('night'), Wd.grade_night, None


def s_sprinklers(L, t, d, ev):
    c = cam_path([(0, (-8, 1.4, 8), (-8, 1.6, 14), 64), (0.45, (-7, 6, 4), (-6, 1, 18), 62),
                  (1.0, (-1, 30, -12), (0, 0, 22), 58)])(t / d)
    em = []
    items = Wd.orchard(L, c, 'normal', 'blanket', t, sprays=True, stoves=True, emissive=em)
    items.append(char(L, 'hero', (-8, 0, 13), t, [(0, ('happy', 'up')), (d * 0.5, ('neutral', 'down'))]))
    return c, items, em, 'night', fog('night'), Wd.grade_night, None


def s_mock(L, t, d, ev):
    td = ev.get('dos', d * 0.5)
    c = cam_path([(0, (0.6, 1.6, 2.6), (2.6, 1.55, 6.0), 66), (td / d, (1.6, 1.5, 2.9), (2.7, 1.6, 6.0), 62),
                  (1.0, (2.2, 1.75, 4.25), (2.75, 1.75, 6.0), 52)])(t / d)
    em = []
    items = Wd.orchard(L, c, 'normal', 'blanket', t, sprays=True, stoves=True, emissive=em)
    laugh = 'laugh' if int(t * 6) % 2 == 0 else 'smug'
    plan = [(0, ('laugh', 'hip'))] + [(k / 6, (('laugh' if k % 2 == 0 else 'smug'), 'hip')) for k in range(int(td * 6))] + \
           [(td, ('smug', 'point'))]
    items.append(char(L, 'vecino', (2.75, 0, 6.0), t, plan, lean_amp=0.06))
    items.append(char(L, 'hero', (-4.0, 0, 12.5), t, [(0, ('worried', 'down')), (td + 0.4, ('sad', 'down'))], h=1.9))
    return c, items, em, 'night', fog('night'), Wd.grade_night, None


def s_dawn(L, t, d, ev):
    c = cam_path([(0, (-8, 1.0, -6), (-8, 1.6, 10), 78), (0.5, (-8, 1.4, 12), (-8, 1.8, 30), 72),
                  (1.0, (-8.5, 2.6, 22), (-6.5, 2.2, 32), 64)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'blanket', t)
    return c, items, [], 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


def s_branch(L, t, d, ev):
    tp = ev.get('parte', d * 0.3)
    shake = 0.05 * math.sin(t * 60) * math.exp(-(t - tp) * 5) if t > tp else 0
    c = cam_path([(0, (-8.8, 1.6, 15.2), (-5, 2.4, 20), 64), (0.5, (-7.6, 2.2, 16.4), (-5, 2.6, 20), 58),
                  (1.0, (-6.2, 2.5, 17.6), (-5.1, 2.5, 20), 54)])(t / d)
    c.pos = c.pos + np.array([shake, shake * 0.5, 0]); c.__init__(c.pos, c.target, c.fov)
    br = (-5, 20) if t > tp else None
    items = Wd.orchard(L, c, 'ice', 'blanket', t, broken_at=br)
    items.append(char(L, 'hero', (-6.6, 0, 18.4), t, [(0, ('worried', 'down')), (tp, ('surprised', 'up')),
                                                     (ev.get('nar', d * 0.7), ('sad', 'down'))], h=1.8))
    return c, items, [], 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


def s_ignored(L, t, d, ev):
    c = cam_path([(0, (-1.8, 1.0, 3.5), (0, 1.3, 10), 62), (1.0, (-1.6, 1.2, 6.5), (0.6, 1.3, 13), 58)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'normal', t)
    items.append(char(L, 'hero', (-1.2, 0, 9.0), t, [(0, ('happy', 'up')), (d * 0.6, ('sad', 'down'))]))
    bz = 6.5 + 6 * (t / d)
    items.append(char(L, 'comprador', (0.9, 0, bz), t, [(0, ('smug', 'down'))], phase=1.0))
    return c, items, [], 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


def s_cut(L, t, d, ev):
    t1, t2, t3 = ev.get('c1', d * 0.35), ev.get('c2', d * 0.6), ev.get('c3', d * 0.75)
    c = cam_path([(0, (5.6, 1.5, 6.5), (8.6, 1.4, 10.5), 62), (0.5, (6.6, 1.6, 7.2), (8.8, 1.5, 10.6), 60),
                  (1.0, (7.4, 1.6, 8.2), (9.2, 1.6, 10.8), 60)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'normal', t)
    items.append(char(L, 'comprador', (8.1, 0, 10.6), t, [(0, ('neutral', 'knife')), (t1, ('surprised', 'knife'))]))
    items.append(char(L, 'vecino', (10.0, 0, 11.2), t, [(0, ('smug', 'hip')), (t1, ('worried', 'down')),
                                                       (t3, ('surprised', 'up'))], phase=0.7))
    # frozen halves popping in front of the camera
    cam = c
    def near(dx, dy, dist, s):
        p = cam.pos + cam.f * dist + cam.r * dx + cam.u * dy
        return billboard(p, s, L.orange_frozen, anchor='center')
    for tt, dx, dy in ((t1, 0.0, -0.05), (t2, -0.35, 0.35), (t3, 0.4, -0.45)):
        k = pop(t, tt)
        if k > 0:
            items.append(near(dx, dy, 1.6, 0.62 * k))
    if t > t3:
        rr = np.random.RandomState(4)
        for i in range(10):
            k = pop(t, t3 + 0.05 * i)
            if k > 0:
                items.append(near(rr.uniform(-1.0, 1.0), rr.uniform(-1.6, 1.2), rr.uniform(2.2, 3.4), 0.5 * k))
    return c, items, [], 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


def s_return(L, t, d, ev):
    tr, ta = ev.get('rompe', d * 0.2), ev.get('apoya', d * 0.7)
    c = cam_path([(0, (-7.2, 2.2, 15.8), (-5.4, 2.1, 19), 60), (0.6, (-6.2, 2.15, 17.3), (-5.6, 2.1, 19), 56),
                  (1.0, (-5.95, 2.12, 18.0), (-5.75, 2.1, 19), 50)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'normal', t, skip={(-5, 20)})
    items.append(billboard((-5, 0, 20), Wd.TREE_H, L.tree_ice[1]))
    items.append(char(L, 'comprador', (-4.3, 0, 20.5), t, [(0, ('neutral', 'down')), (tr, ('neutral', 'knife'))]))
    s = 0.55
    items.append(billboard((-5.75, 2.1, 19.0), s, L.orange_ice if t < tr else L.orange_ice, anchor='center', depth_bias=2))
    if t > tr:
        k = pop(t, tr)
        rr = np.random.RandomState(1)
        for i in range(6):  # ice shards flying
            a = rr.uniform(0, 6.28); dd = (t - tr) * 0.9
            items.append(billboard((-5.75 + math.cos(a) * dd, 2.1 + math.sin(a) * dd - (t - tr) ** 2, 19.0), 0.12, L.drop_ice,
                                   anchor='center', depth_bias=2))
    kx = -5.75 + 0.9 * (1 - ease((t - tr) / max(0.1, ta - tr)))
    items.append(billboard((kx + 0.35, 2.22, 18.95), 0.16, L.knife, w=0.7, anchor='center', depth_bias=3))
    return c, items, [], 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


ORB = np.array([-5.75, 2.1, 19.0])


def orbit_cam(t, d, a0, a1, r0, r1, h0, h1, tgt, fov=55):
    u = ease(t / d) * 0.6 + (t / d) * 0.4
    a = a0 + (a1 - a0) * u; r = r0 + (r1 - r0) * u; h = h0 + (h1 - h0) * u
    p = tgt + np.array([math.sin(a) * r, h, -math.cos(a) * r])
    return Camera(p, tgt, fov=fov)


def drops(L, t, center, n=8, ice_y=0.25, emissive=None, heat=True):
    out = []
    rr = np.random.RandomState(3)
    for i in range(n):
        ph = rr.uniform(0, 1); x = rr.uniform(-0.25, 0.25); z = rr.uniform(-0.1, 0.1)
        u = (t * 0.9 + ph) % 1.0
        y = 1.3 - u * 1.3
        if y > ice_y:
            out.append(billboard(center + [x, y, z], 0.1, L.drop, anchor='center', depth_bias=2))
        else:
            out.append(billboard(center + [x, ice_y * 0.6, z], 0.09, L.drop_ice, anchor='center', depth_bias=2))
            if heat and emissive is not None:
                k = (ice_y - y) / ice_y
                emissive.append(billboard(center + [x * (1 + k * 3), ice_y + k * 0.9, z], 0.16 * (1 - k * 0.4), L.heat,
                                          anchor='center', mode='add', opacity=max(0, 1 - k)))
    return out


def s_explain(L, t, d, ev):
    c = orbit_cam(t, d, -0.9, 0.2, 1.6, 1.25, 0.2, 0.05, ORB, fov=55)
    em = []
    items = Wd.orchard(L, c, 'ice', 'normal', t, skip={(-5, 20)})
    items.append(billboard((-5, 0, 20), Wd.TREE_H, L.tree_ice[1], opacity=0.5))
    items.append(billboard(ORB, 0.6, L.orange_ice, anchor='center', depth_bias=2))
    items += drops(L, t, ORB, 10, 0.3, em)
    tc = ev.get('calor', d * 0.6)
    k = pop(t, tc)
    if k > 0:
        em.append(billboard(ORB, 1.4 * k, L.glow_y, anchor='center', mode='add', opacity=0.6))
        items.append(billboard(ORB + [0, 0.62, 0], 0.26 * k, L.label_calor, anchor='center', depth_bias=3))
    return c, items, em, 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


def s_zero(L, t, d, ev):
    c = orbit_cam(t, d, 0.2, 1.1, 1.3, 1.5, 0.05, 0.12, ORB + [0.25, 0, 0], fov=55)
    em = []
    items = Wd.orchard(L, c, 'ice', 'normal', t, skip={(-5, 20)})
    items.append(billboard((-5, 0, 20), Wd.TREE_H, L.tree_ice[1], opacity=0.5))
    items.append(billboard(ORB, 0.6, L.orange_ice, anchor='center', depth_bias=2))
    items += drops(L, t, ORB, 10, 0.3, em)
    k = pop(t, ev.get('cero', d * 0.75) - 0.6)
    tp = ORB + [0.6, 0, 0]
    if k > 0:
        items.append(billboard(tp, 1.0 * k, L.thermo_0, anchor='center', depth_bias=2.5))
        pulse = 0.5 + 0.3 * math.sin(t * 9)
        em.append(billboard(tp + [0, 0.13, 0], 0.5 * k, L.glow_m, w=0.7, anchor='center', mode='add', opacity=pulse))
    return c, items, em, 'dawn', fog('dawn'), Wd.grade_dawn, Wd.ice_ground


POT = np.array([-11.0, 0.55, -8.0])


def s_pot(L, t, d, ev):
    c = orbit_cam(t, d, 2.6, 3.3, 2.9, 2.5, 0.75, 0.55, POT + [0, 0.15, 0], fov=56)
    em = []
    items = Wd.orchard(L, c, 'ice', 'normal', t)
    pp = POT - c.r * 0.22
    items.append(billboard(pp - [0, 0.55, 0], 0.95, L.pot))
    em.append(billboard(pp - [0, 0.9, 0], 1.0, L.glow, w=1.5, mode='add', opacity=0.5 + 0.2 * math.sin(t * 13)))
    k = pop(t, ev.get('cien', d * 0.5) - 0.3)
    if k > 0:
        items.append(billboard(POT + c.r * 0.42 + [0, 0.35, 0], 1.45 * k, L.thermo_100, anchor='center', depth_bias=1))
    return c, items, em, 'day', fog('day'), None, Wd.ice_ground


def s_scale(L, t, d, ev):
    tp = np.array([-1.0, 1.4, 8.0])
    u = t / d
    c = Camera(tp + [0.15 * math.sin(u * 3), 0.55 - 0.75 * ease(u), -2.7 + 0.35 * u], tp + [0, 0.35 - 0.6 * ease(u), 0], fov=52)
    em = []
    items = Wd.orchard(L, c, 'ice', 'normal', t)
    items.append(billboard(tp, 2.6, L.thermo_scale, anchor='center'))
    k = pop(t, ev.get('dos2', d * 0.7) - 0.15)
    # mark at -2: thermometer spans lo=-8..hi=4; compute y of -2 on the card
    card_h = 2.6; ty0, ty1, H = 60, 1100 - 220, 1100
    yy = ty1 - (-2 + 8) / 12 * (ty1 - ty0)
    wy = tp[1] + card_h / 2 - yy / H * card_h
    if k > 0:
        items.append(billboard(np.array([tp[0], wy, tp[2] - 0.05]) - c.r * 0.52, 0.34 * k, L.orange_frozen, anchor='center', depth_bias=1))
        items.append(billboard(np.array([tp[0], wy + 0.3, tp[2] - 0.05]) - c.r * 0.5, 0.17 * k, L.label_m2, anchor='center', depth_bias=1))
        em.append(billboard([tp[0], wy, tp[2] - 0.1], 0.5, L.glow_y, w=1.6, anchor='center', mode='add', opacity=0.55))
    return c, items, em, 'day', fog('day'), None, Wd.ice_ground


def s_juice(L, t, d, ev):
    c = cam_path([(0, (-7.0, 1.9, 16.6), (-5.2, 1.7, 19.5), 60), (1.0, (-6.6, 1.75, 17.4), (-5.3, 1.7, 19.5), 56)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'normal', t)
    items.append(char(L, 'comprador', (-5.0, 0, 19.6), t, [(0, ('surprised', 'knife')), (0.5, ('happy', 'up'))]))
    items.append(char(L, 'hero', (-6.2, 0, 20.4), t, [(0, ('surprised', 'down')), (0.6, ('happy', 'up'))], phase=1.3))
    k = pop(t, 0.05)
    p = c.pos + c.f * 1.3 + c.u * -0.1
    items.append(billboard(p, 0.75 * k, L.orange_juicy, anchor='center'))
    rr = np.random.RandomState(7)
    for i in range(14):
        a = rr.uniform(-0.3, 3.4); sp = rr.uniform(0.6, 1.4); tt = t * sp
        q = p + c.r * math.cos(a) * (0.3 + tt) + c.u * (math.sin(a) * (0.3 + tt) - 0.8 * tt * tt) - c.f * 0.05
        items.append(billboard(q, 0.07, L.drop, anchor='center', depth_bias=1))
    return c, items, [], 'day', fog('day'), None, Wd.ice_ground


def s_angry(L, t, d, ev):
    c = cam_path([(0, (6.2, 1.6, 7.4), (8.0, 1.6, 11), 60), (1.0, (7.4, 1.72, 9.4), (8.0, 1.72, 11), 50)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'blanket', t)
    items.append(char(L, 'vecino', (8.0, 0, 11.0), t, [(0, ('worried', 'down')), (0.35, ('angry', 'up'))], lean_amp=0.07))
    return c, items, [], 'day', fog('day'), None, Wd.ice_ground


def s_final(L, t, d, ev):
    tf = ev.get('firma', 0.4)
    c = cam_path([(0, (-1.6, 1.5, 5.0), (0, 1.4, 9), 60), (0.45, (-2.0, 3.5, 3.0), (-1, 1.3, 10), 62),
                  (1.0, (-8, 26, -10), (-8, 0, 22), 60)])(t / d)
    items = Wd.orchard(L, c, 'ice', 'blanket', t)
    items.append(char(L, 'comprador', (0.5, 0, 9.0), t, [(0, ('happy', 'point')), (tf, ('happy', 'up'))]))
    items.append(char(L, 'hero', (-0.7, 0, 9.2), t, [(0, ('happy', 'point')), (tf + 0.3, ('happy', 'up'))], phase=0.8))
    k = pop(t, tf)
    if k > 0:
        items.append(billboard((-0.1, 1.9, 8.8), 1.0 * k, L.contract, anchor='center', depth_bias=1))
    return c, items, [], 'day', fog('day'), None, Wd.ice_ground


SHOTS = [s_hook, s_buyer, s_forecast, s_stoves, s_sprinklers, s_mock, s_dawn, s_branch, s_ignored, s_cut, s_return,
         s_explain, s_zero, s_pot, s_scale, s_juice, s_angry, s_final]
assert len(SHOTS) == len(SHOT_START), (len(SHOTS), len(SHOT_START))
