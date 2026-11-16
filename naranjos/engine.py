"""Mini 3D engine (PIL + numpy): ray-cast ground & sky, perspective-textured quads, painter's algorithm."""
import math
import numpy as np
from PIL import Image

UP = np.array([0.0, 1.0, 0.0])


def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


class Camera:
    def __init__(self, pos, target, fov=62.0, roll=0.0, W=720, H=1280):
        self.pos = np.asarray(pos, float); self.target = np.asarray(target, float)
        self.fov = fov; self.roll = roll; self.W = W; self.H = H
        f = norm(self.target - self.pos)
        r = norm(np.cross(f, UP))
        u = np.cross(r, f)
        if roll:
            c, s = math.cos(roll), math.sin(roll)
            r, u = r * c + u * s, -r * s + u * c
        self.f, self.r, self.u = f, r, u
        self.fpx = (H / 2) / math.tan(math.radians(fov) / 2)

    def project(self, P):
        """P: (N,3) -> (N,2) screen, depth (N,)"""
        v = np.asarray(P, float) - self.pos
        z = v @ self.f
        x = v @ self.r; y = v @ self.u
        zz = np.where(z > 1e-6, z, 1e-6)
        sx = self.W / 2 + x / zz * self.fpx
        sy = self.H / 2 - y / zz * self.fpx
        return np.stack([sx, sy], -1), z


class World:
    """Holds sky panorama, ground map and grading."""

    def __init__(self, sky, ground, detail, ground_box=(-64, 64, -40, 88), far_col=(118, 150, 52)):
        self.sky = np.asarray(sky)            # H,W,3
        self.ground = np.asarray(ground).astype(np.float32)  # H,W,3
        self.detail = np.asarray(detail).astype(np.float32) / 128.0
        self.box = ground_box
        self.far_col = np.array(far_col, np.float32)

    def background(self, cam, fog_col, fog_dist=90.0, ground_tint=None):
        W, H = cam.W, cam.H
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        dx = (xs - W / 2) / cam.fpx; dy = -(ys - H / 2) / cam.fpx
        D = cam.f[None, None, :] + dx[..., None] * cam.r[None, None, :] + dy[..., None] * cam.u[None, None, :]
        D /= np.linalg.norm(D, axis=-1, keepdims=True)
        out = np.empty((H, W, 3), np.float32)
        # sky
        az = np.arctan2(D[..., 0], D[..., 2])
        el = np.arcsin(np.clip(D[..., 1], -1, 1))
        sh, sw, _ = self.sky.shape
        u = ((az / (2 * np.pi)) % 1.0) * (sw - 1)
        v = np.clip((1.35 - el) / 1.6, 0, 1) * (sh - 1)
        out[:] = self.sky[v.astype(np.int32), u.astype(np.int32)]
        # ground
        gmask = D[..., 1] < -1e-4
        if cam.pos[1] > 0 and gmask.any():
            t = -cam.pos[1] / D[..., 1][gmask]
            gx = cam.pos[0] + D[..., 0][gmask] * t
            gz = cam.pos[2] + D[..., 2][gmask] * t
            x0, x1, z0, z1 = self.box
            gh, gw, _ = self.ground.shape
            gu = (gx - x0) / (x1 - x0) * (gw - 1); gv = (gz - z0) / (z1 - z0) * (gh - 1)
            inside = (gu >= 0) & (gu < gw - 1) & (gv >= 0) & (gv < gh - 1)
            col = np.empty((gx.shape[0], 3), np.float32); col[:] = self.far_col
            gu = gu[inside]; gv = gv[inside]
            i0 = gv.astype(np.int32); j0 = gu.astype(np.int32); fy = (gv - i0)[:, None]; fx = (gu - j0)[:, None]
            G = self.ground
            col[inside] = (G[i0, j0] * (1 - fx) * (1 - fy) + G[i0, j0 + 1] * fx * (1 - fy) +
                           G[i0 + 1, j0] * (1 - fx) * fy + G[i0 + 1, j0 + 1] * fx * fy)
            ds = self.detail.shape[0]
            dd = self.detail[((gz * 24) % ds).astype(np.int32), ((gx * 24) % ds).astype(np.int32)]
            col *= (0.75 + 0.25 * dd)[:, None]
            if ground_tint is not None:
                col = ground_tint(gx, gz, col)
            dist = t
            fog = np.clip((dist - fog_dist * 0.25) / fog_dist, 0, 0.85)[:, None]
            col = col * (1 - fog) + np.asarray(fog_col, np.float32) * fog
            out[gmask] = col
        return out


def homography(src, dst):
    """Solve H mapping dst->src (PIL convention: output coords -> input coords)."""
    A = []; b = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    try:
        return np.linalg.solve(np.array(A, float), np.array(b, float))
    except np.linalg.LinAlgError:
        return None


def draw_quad(frame, cam, corners, tex, mode='over', opacity=1.0, near=0.15):
    """corners: 4x3 world points ordered TL, TR, BR, BL (texture corners)."""
    scr, z = cam.project(corners)
    if (z < near).any():
        return
    W, H = cam.W, cam.H
    x0 = max(0, int(math.floor(scr[:, 0].min()))); x1 = min(W, int(math.ceil(scr[:, 0].max())))
    y0 = max(0, int(math.floor(scr[:, 1].min()))); y1 = min(H, int(math.ceil(scr[:, 1].max())))
    if x1 - x0 < 1 or y1 - y0 < 1:
        return
    # skip degenerate (edge-on)
    a = scr
    area = 0.5 * abs(np.dot(a[:, 0], np.roll(a[:, 1], 1)) - np.dot(a[:, 1], np.roll(a[:, 0], 1)))
    if area < 2:
        return
    tw, th = tex.size
    src = [(0, 0), (tw, 0), (tw, th), (0, th)]
    dst = [(p[0] - x0, p[1] - y0) for p in scr]
    coef = homography(src, dst)
    if coef is None:
        return
    # choose a smaller mip level when heavily minified
    scale = math.sqrt(area / (tw * th))
    t = tex
    if scale < 0.5:
        lvl = min(4, int(math.log2(1 / scale)))
        t = mip(tex, lvl)
        f = tex.size[0] / t.size[0]
        coef = coef.copy(); coef[0:3] /= f; coef[3:6] /= f
    patch = t.transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(coef), Image.BILINEAR)
    if opacity < 1:
        al = patch.getchannel('A').point(lambda v: int(v * opacity)); patch.putalpha(al)
    if mode == 'add':
        p = np.asarray(patch, np.float32)
        reg = frame[y0:y1, x0:x1]
        reg += p[..., :3] * (p[..., 3:4] / 255.0) * opacity
    else:
        p = np.asarray(patch, np.float32)
        al = p[..., 3:4] / 255.0
        reg = frame[y0:y1, x0:x1]
        reg *= (1 - al); reg += p[..., :3] * al


_MIP = {}
_TINT = {}


def tinted(tex, tint):
    k = (id(tex), tint)
    if k not in _TINT:
        a = np.asarray(tex).astype(np.float32)
        a[..., :3] *= np.array(tint, np.float32)
        _TINT[k] = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        _TINT[k]._keep = tex
    return _TINT[k]


def mip(tex, lvl):
    k = (id(tex), lvl)
    if k not in _MIP:
        w, h = tex.size
        _MIP[k] = tex.resize((max(1, w >> lvl), max(1, h >> lvl)), Image.BOX)
    return _MIP[k]


# ------------------------------------------------------------- items
def billboard(pos, h, tex, w=None, lean=0.0, depth_bias=0.0, mode='over', opacity=1.0, face=None, anchor='bottom',
              flip=False, layer=0):
    """Vertical card standing at pos (feet). Faces camera unless face (yaw radians) given."""
    if w is None:
        w = h * tex.size[0] / tex.size[1]
    return dict(kind='bb', pos=np.asarray(pos, float), h=h, w=w, tex=tex, lean=lean, bias=depth_bias, mode=mode,
                opacity=opacity, face=face, anchor=anchor, flip=flip, layer=layer)


def flat(center, w, d, tex, yaw=0.0, y=0.01, mode='over', opacity=1.0, layer=-1):
    """Horizontal decal on the ground."""
    return dict(kind='flat', pos=np.asarray(center, float), w=w, d=d, tex=tex, yaw=yaw, y=y, mode=mode, opacity=opacity,
                layer=layer)


def quad(corners, tex, mode='over', opacity=1.0, layer=0, bias=0.0):
    return dict(kind='quad', corners=np.asarray(corners, float), tex=tex, mode=mode, opacity=opacity, layer=layer, bias=bias)


def item_corners(it, cam):
    if it['kind'] == 'quad':
        return it['corners']
    if it['kind'] == 'flat':
        c = it['pos']; cy, sy = math.cos(it['yaw']), math.sin(it['yaw'])
        ax = np.array([cy, 0, -sy]) * it['w'] / 2; az = np.array([sy, 0, cy]) * it['d'] / 2
        base = np.array([c[0], it['y'], c[2]])
        return np.array([base - ax + az, base + ax + az, base + ax - az, base - ax - az])
    p = it['pos']
    if it['face'] is None:
        r = cam.r.copy(); r[1] = 0; r = norm(r)
    else:
        r = np.array([math.cos(it['face']), 0, -math.sin(it['face'])])
    if it['flip']:
        r = -r
    hw = it['w'] / 2; h = it['h']
    fwd = np.cross(UP, r)  # toward camera-ish
    lean = it['lean']
    top_off = UP * h + r * (lean * h)
    if it['anchor'] == 'center':
        b = p - UP * h / 2
    else:
        b = p
    return np.array([b - r * hw + top_off, b + r * hw + top_off, b + r * hw, b - r * hw])


def render(cam, world, items, fog_col, grade=None, ground_tint=None, emissive=(), post_tint=None):
    frame = world.background(cam, fog_col, ground_tint=ground_tint)
    prepared = []
    for it in items:
        c = item_corners(it, cam)
        cen = c.mean(0)
        if it['kind'] == 'bb':
            cen = it['pos'] + UP * 0.0
        dpt = float((cen - cam.pos) @ cam.f) - it.get('bias', 0.0)
        prepared.append((it['layer'] if it['kind'] == 'flat' else 0, -dpt, id(it), it, c))
    prepared.sort(key=lambda x: (x[0], x[1]))
    post = []
    for _, d_, _, it, c in prepared:
        if it.get('post'):
            post.append((d_, it, c)); continue
        draw_quad(frame, cam, c, it['tex'], it['mode'], it['opacity'])
    if grade is not None:
        frame = grade(frame)
    for _, it, c in sorted(post, key=lambda x: x[0]):
        tex = it['tex'] if post_tint is None else tinted(it['tex'], post_tint)
        draw_quad(frame, cam, c, tex, it['mode'], it['opacity'])
    for it in emissive:
        c = item_corners(it, cam)
        draw_quad(frame, cam, c, it['tex'], it['mode'], it['opacity'])
    return frame


# ------------------------------------------------------------- camera path
def hermite_path(keys):
    """keys: list of (t, value ndarray). Bounded-tangent Hermite (no overshoot on uneven spacing)."""
    ts = [k[0] for k in keys]; vs = [np.asarray(k[1], float) for k in keys]
    n = len(keys)
    m = []
    for i in range(n):
        if i == 0:
            s = (vs[1] - vs[0]) / (ts[1] - ts[0]); m.append(s * 0.5)
        elif i == n - 1:
            s = (vs[-1] - vs[-2]) / (ts[-1] - ts[-2]); m.append(s * 0.5)
        else:
            s0 = (vs[i] - vs[i - 1]) / (ts[i] - ts[i - 1]); s1 = (vs[i + 1] - vs[i]) / (ts[i + 1] - ts[i])
            cr = (vs[i + 1] - vs[i - 1]) / (ts[i + 1] - ts[i - 1])
            lim = min(np.linalg.norm(s0), np.linalg.norm(s1))
            nc = np.linalg.norm(cr)
            if nc > lim and nc > 1e-9:
                cr = cr * (lim / nc)
            m.append(cr)

    def f(t):
        if t <= ts[0]:
            return vs[0]
        if t >= ts[-1]:
            return vs[-1]
        i = max(j for j in range(n - 1) if ts[j] <= t)
        h = ts[i + 1] - ts[i]; u = (t - ts[i]) / h
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u
        h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        return h00 * vs[i] + h10 * h * m[i] + h01 * vs[i + 1] + h11 * h * m[i + 1]
    return f
