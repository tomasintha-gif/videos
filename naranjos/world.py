"""Static world: orchard of two farms split by a road, houses, fences, stoves, sprinklers."""
import math
import numpy as np
from PIL import Image
import assets as A
from engine import World, billboard, flat, quad

TREE_H = 4.2


class Lib:
    def __init__(self):
        self.sky = {k: A.make_sky(k) for k in ('day', 'dawn', 'night')}
        self.ground = A.make_ground()
        self.detail = A.make_detail()
        self.worlds = {k: World(self.sky[k], self.ground, self.detail) for k in self.sky}
        self.tree = [A.make_tree('normal', s) for s in range(1, 5)]
        self.tree_ice = [A.make_tree('ice', s) for s in range(1, 5)]
        self.tree_ice_broken = A.make_tree('ice', 2, broken=True)
        self.tree_blanket = [A.make_tree('blanket', s) for s in range(1, 4)]
        self.spray = [A.make_spray(s) for s in range(3)]
        self.stove = A.make_stove()
        self.flame = [A.make_flame(s) for s in range(3)]
        self.glow = A.make_glow((255, 140, 40))
        self.glow_y = A.make_glow((255, 220, 90))
        self.glow_m = A.make_glow((255, 60, 210))
        self.glow_c = A.make_glow((140, 210, 255))
        self.shadow = A.make_shadow()
        self.house = A.make_house(); self.roof = A.make_roof()
        self.fence = A.make_fence()
        self.chars = {}
        self.sign_buyer = A.make_sign(['SE BUSCA', 'UNA FINCA', 'PARA TODO', 'EL INVIERNO'], W=900, H=620,
                                      colors=[(255, 220, 120), (250, 240, 214), (250, 240, 214), (250, 240, 214)])
        self.news = A.make_newspaper()
        self.thermo_m5 = A.make_thermo(-5, marks=(0, -5))
        self.thermo_0 = A.make_thermo(0, marks=(0,), glow=(255, 40, 200), label='0°C')
        self.thermo_scale = A.make_thermo(-5, marks=(0, -2, -5), glow=(255, 200, 40))
        self.orange_frozen = A.make_orange_half('frozen')
        self.orange_juicy = A.make_orange_half('juicy')
        self.orange_ice = A.make_orange_half('whole_ice')
        self.knife = A.make_knife()
        self.pot = A.make_pot()
        self.heat = A.make_heat_particle()
        self.drop = A.make_drop(); self.drop_ice = A.make_drop(ice=True)
        self.contract = A.make_contract()
        self.thermo_100 = A.make_thermo(100, lo=0, hi=110, marks=(100,), glow=(255, 200, 40), label='100°C')
        self.label_calor = self._label('CALOR', (255, 210, 60))
        self.label_m2 = self._label('-2°C', (120, 200, 255))

    def _label(self, txt, col):
        f = A.font(160)
        from PIL import ImageDraw
        img = Image.new('RGBA', (900, 240), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        d.text((450, 120), txt, font=f, fill=col + (255,), anchor='mm', stroke_width=14, stroke_fill=(20, 18, 20, 255))
        return img

    def char(self, kind, expr='neutral', arms='down', blink=False):
        k = (kind, expr, arms, blink)
        if k not in self.chars:
            self.chars[k] = A.make_char(kind, expr, arms, blink)
        return self.chars[k]


HERO_ROWS = [-5 - 6 * i for i in range(6)]
VEC_ROWS = [5 + 6 * i for i in range(6)]
ZS = [4 * i for i in range(16)]  # 0..60


def tree_list():
    out = []
    for side, rows in ((-1, HERO_ROWS), (1, VEC_ROWS)):
        for i, x in enumerate(rows):
            for j, z in enumerate(ZS):
                out.append((side, x + ((i * 7 + j * 3) % 5 - 2) * 0.08, z, (i * 5 + j * 3) % 4))
    return out


TREES = tree_list()


def visible(cam, p, rad=4.0, maxd=75.0):
    v = np.asarray(p, float) - cam.pos
    z = v @ cam.f
    if z < -rad or z > maxd:
        return False
    # loose frustum check
    x = abs(v @ cam.r); y = abs(v @ cam.u)
    lim = (z + rad) * (cam.W / 2 / cam.fpx) + rad * 1.5
    limy = (z + rad) * (cam.H / 2 / cam.fpx) + rad * 1.5
    return x < lim and y < limy


def orchard(L, cam, hero_state='normal', vec_state='normal', t=0.0, sprays=False, stoves=False, broken_at=None,
            emissive=None, skip=()):
    """Returns items. hero_state: normal|ice ; vec_state: normal|blanket."""
    items = []
    for side, x, z, k in TREES:
        p = (x, 0, z)
        if (round(x), z) in skip:
            continue
        if not visible(cam, p):
            continue
        if side < 0:
            if hero_state == 'ice':
                tex = L.tree_ice_broken if broken_at == (round(x), z) else L.tree_ice[k]
            else:
                tex = L.tree[k]
        else:
            tex = L.tree_blanket[k % 3] if vec_state == 'blanket' else L.tree[k]
        items.append(billboard(p, TREE_H, tex))
        items.append(flat((x + 1.0, 0, z + 0.9), 4.2, 2.6, L.shadow, yaw=0.5))
        if side < 0 and sprays:
            fr = L.spray[(int(t * 12) + k) % 3]
            items.append(billboard((x, 2.9, z), 2.4, fr, w=5.4, depth_bias=0.4))
        if side > 0 and stoves and k % 2 == 0:
            sp = (x + 3, 0, z + 2)
            if visible(cam, sp, 2, 60):
                items.append(billboard(sp, 1.1, L.stove))
                if emissive is not None:
                    fr = L.flame[(int(t * 10) + k) % 3]
                    emissive.append(billboard((sp[0], 1.0, sp[2]), 0.55, fr, mode='add', opacity=0.9))
                    emissive.append(billboard((sp[0], -0.6, sp[2]), 3.2, L.glow, w=3.6, mode='add', opacity=0.55))
    # fences along the road
    for xf in (-2.3, 2.3):
        items.append(quad([(xf, 1.4, -12), (xf, 1.4, 68), (xf, 0, 68), (xf, 0, -12)], L.fence))
    # houses (boxes)
    for hx, flipx in ((-14, 1), (14, -1)):
        items += house(L, cam, hx, -14, 8, 4, 6)
    return items


def house(L, cam, cx, cz, w, h, d):
    x0, x1 = cx - w / 2, cx + w / 2; z0, z1 = cz - d / 2, cz + d / 2
    it = []
    walls = [
        [(x0, h, z0), (x1, h, z0), (x1, 0, z0), (x0, 0, z0)],
        [(x1, h, z1), (x0, h, z1), (x0, 0, z1), (x1, 0, z1)],
        [(x0, h, z1), (x0, h, z0), (x0, 0, z0), (x0, 0, z1)],
        [(x1, h, z0), (x1, h, z1), (x1, 0, z1), (x1, 0, z0)],
    ]
    for wq in walls:
        c = np.array(wq)
        nrm = np.cross(c[1] - c[0], c[3] - c[0])
        if (cam.pos - c.mean(0)) @ nrm < 0:  # back-face cull (outward normal check)
            pass
        it.append(quad(wq, L.house))
    ry = h + 2.2
    it.append(quad([(x0 - 0.5, ry, cz), (x1 + 0.5, ry, cz), (x1 + 0.5, h - 0.3, z1 + 0.6), (x0 - 0.5, h - 0.3, z1 + 0.6)], L.roof, bias=-0.5))
    it.append(quad([(x1 + 0.5, ry, cz), (x0 - 0.5, ry, cz), (x0 - 0.5, h - 0.3, z0 - 0.6), (x1 + 0.5, h - 0.3, z0 - 0.6)], L.roof, bias=-0.5))
    return it


# ------------------------------------------------------------- grades
def grade_night(fr):
    fr *= np.array([0.30, 0.40, 0.78], np.float32)
    fr += np.array([4, 8, 20], np.float32)
    return fr


def grade_dusk(fr):
    fr *= np.array([1.02, 0.80, 0.78], np.float32)
    return fr


def grade_dawn(fr):
    fr *= np.array([1.04, 0.98, 1.02], np.float32)
    fr += np.array([10, 6, 14], np.float32)
    return fr


def ice_ground(gx, gz, col):
    """Hero side (x<-2.3) gets an icy glaze in the morning."""
    m = (gx < -2.4)
    c = col.copy()
    c[m] = c[m] * 0.45 + np.array([200, 228, 245], np.float32) * 0.55
    return c
