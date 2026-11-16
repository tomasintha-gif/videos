"""Characters, vultures and props for 'El día que llovió carne'."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'naranjos'))
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import assets as A
from assets import strokes, wobble_poly, outline, font, posterize, shrink, rng, INK

S = 2

OUT = {
    'crouch': dict(body=(138, 70, 120), body2=(110, 52, 96), hat='bonnet', apron=True, hair=(120, 70, 40)),
    'silas': dict(body=(56, 92, 160), body2=(40, 70, 130), hat='straw', straps=True, shirt=(214, 70, 60)),
    'ezra': dict(body=(70, 120, 90), body2=(50, 96, 70), hat='cap', beard=(120, 74, 40)),
    'doctor': dict(body=(36, 36, 44), body2=(24, 24, 30), hat='bowler', glasses=True, collar=True, moustache=True),
    'expert1': dict(body=(110, 112, 124), body2=(86, 88, 100), hat='tophat', monocle=True, collar=True),
    'expert2': dict(body=(140, 96, 60), body2=(114, 76, 44), hat=None, bald=True, glasses=True, collar=True),
}


def _hat(img, d, kind, hx, hy, hr):
    if kind == 'straw':
        brim = wobble_poly(hx, hy - hr * 0.78, hr * 1.35, hr * 0.22, 5, 40, 0.03)
        crown = [(hx - hr * 0.6, hy - hr * 0.82), (hx - hr * 0.5, hy - hr * 1.32), (hx + hr * 0.5, hy - hr * 1.32),
                 (hx + hr * 0.6, hy - hr * 0.82)]
        d.polygon(brim, fill=(232, 196, 110, 255)); d.polygon(crown, fill=(240, 206, 120, 255))
        m = Image.new('L', img.size, 0); md = ImageDraw.Draw(m); md.polygon(brim, fill=255); md.polygon(crown, fill=255)
        strokes(img, (hx - hr * 1.4, hy - hr * 1.4, hx + hr * 1.4, hy - hr * 0.5), [(200, 160, 80), (250, 220, 150)], 160, 3,
                (10 * S, 24 * S), 160, angle=0.0, mask=m)
        d = ImageDraw.Draw(img); outline(d, brim, 11 * S); outline(d, crown, 11 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 0.98, hx + hr * 0.58, hy - hr * 0.86], fill=(60, 90, 160, 255))
    elif kind == 'bowler':
        d.ellipse([hx - hr * 1.0, hy - hr * 0.95, hx + hr * 1.0, hy - hr * 0.68], fill=(30, 28, 30, 255), outline=INK, width=8 * S)
        d.chord([hx - hr * 0.68, hy - hr * 1.5, hx + hr * 0.68, hy - hr * 0.5], 180, 360, fill=(36, 34, 38, 255), outline=INK,
                width=8 * S)
    elif kind == 'tophat':
        d.ellipse([hx - hr * 0.95, hy - hr * 0.98, hx + hr * 0.95, hy - hr * 0.72], fill=(24, 22, 26, 255), outline=INK, width=8 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 1.75, hx + hr * 0.58, hy - hr * 0.86], fill=(30, 28, 34, 255), outline=INK,
                    width=8 * S)
        d.rectangle([hx - hr * 0.58, hy - hr * 1.06, hx + hr * 0.58, hy - hr * 0.92], fill=(90, 90, 100, 255))
    elif kind == 'cap':
        cap = [(hx - hr * 0.95, hy - hr * 0.55), (hx - hr * 0.8, hy - hr * 1.02), (hx + hr * 0.3, hy - hr * 1.12),
               (hx + hr * 1.0, hy - hr * 0.8), (hx + hr * 1.45, hy - hr * 0.62), (hx + hr * 0.95, hy - hr * 0.5)]
        d.polygon(cap, fill=(130, 92, 58, 255)); outline(d, cap, 10 * S)
        d.line([(hx - hr * 0.2, hy - hr * 1.1), (hx + hr * 0.1, hy - hr * 0.6)], fill=(90, 60, 36, 255), width=6 * S)
    elif kind == 'bonnet':
        bon = wobble_poly(hx, hy - hr * 0.3, hr * 1.18, hr * 0.98, 9, 48, 0.02)
        bon = [p for p in bon if p[1] < hy + hr * 0.15]
        d.polygon(bon, fill=(150, 196, 232, 255)); outline(d, bon, 11 * S)
        # face opening redraw is done by caller (head drawn after)
    return ImageDraw.Draw(img)


def make_char(kind, expr='neutral', arms='down', legs='stand', blink=False, frame=0, prop=None):
    W, H = 640 * S, 1100 * S
    sp = OUT[kind]
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    hx, hy, hr = W / 2, 420 * S, 215 * S
    seed = hash(kind) % 97
    # legs
    lp = {'stand': [(-1, 0, 0), (1, 0, 0)], 'runA': [(-1, -60, -40), (1, 70, 0)], 'runB': [(-1, 60, 0), (1, -70, -40)],
          'sit': [(-1, 90, -120), (1, 90, -120)]}[legs]
    for sx, dx, lift in lp:
        x = W / 2 + sx * 55 * S
        fx = x + sx * 10 * S + dx * S; fy = 1060 * S + lift * S
        if legs == 'sit':
            d.line([(x, 860 * S), (x + 120 * S * (1 if sx > 0 else 0.8), 900 * S), (x + 120 * S, 1060 * S)], fill=INK, width=16 * S,
                   joint='curve'); fx = x + 120 * S
        else:
            d.line([(x, 860 * S), (fx, fy)], fill=INK, width=16 * S)
        d.ellipse([fx - 40 * S + sx * 18 * S, fy - 20 * S, fx + 40 * S + sx * 18 * S, fy + 30 * S], fill=INK)
    sh_y = 690 * S
    hands = {}
    arm_t = {'down': {-1: (-150, 260), 1: (150, 260)}, 'up': {-1: (-190, -170), 1: (190, -170)},
             'point': {-1: (-150, 260), 1: (260, -40)}, 'eat': {-1: (-150, 260), 1: (60, -150)},
             'hold': {-1: (-150, 260), 1: (150, 70)}, 'stir': {-1: (-90, 160), 1: (110, 120)},
             'runA': {-1: (-200, 60), 1: (170, 220)}, 'runB': {-1: (-170, 220), 1: (200, 60)},
             'magnify': {-1: (-150, 260), 1: (200, -20)}, 'shrug': {-1: (-230, -40), 1: (230, -40)},
             'yawn': {-1: (-210, -200), 1: (210, -200)}, 'cover': {-1: (-60, -170), 1: (60, -170)},
             'lap': {-1: (-70, 200), 1: (70, 200)}, 'bag': {-1: (-150, 260), 1: (170, 240)}}[arms]
    for sx in (-1, 1):
        x0 = W / 2 + sx * 120 * S
        dx, dy = arm_t[sx]
        end = (W / 2 + dx * S, sh_y + dy * S)
        mid = ((x0 + end[0]) / 2 + sx * 30 * S, (sh_y + end[1]) / 2 + 20 * S)
        hands[sx] = end
    # dress / body
    if sp.get('apron') or kind == 'crouch':
        body = [(W / 2 - 120 * S, 610 * S), (W / 2 + 120 * S, 610 * S), (W / 2 + 200 * S, 940 * S), (W / 2 - 200 * S, 940 * S)]
        body = wobble_poly(W / 2, 780 * S, 175 * S, 165 * S, seed + 10, 40, 0.04)
    else:
        body = wobble_poly(W / 2, 745 * S, 150 * S, 140 * S, seed + 10, 40, 0.04)
    d.polygon(body, fill=sp['body'] + (255,))
    bm = Image.new('L', (W, H), 0); ImageDraw.Draw(bm).polygon(body, fill=255)
    strokes(img, (W / 2 - 200 * S, 580 * S, W / 2 + 200 * S, 960 * S), [sp['body2'], tuple(min(255, c + 30) for c in sp['body'])],
            260, seed, (12 * S, 34 * S), 200, mask=bm)
    d = ImageDraw.Draw(img)
    if sp.get('apron'):
        ap = [(W / 2 - 90 * S, 700 * S), (W / 2 + 90 * S, 700 * S), (W / 2 + 110 * S, 920 * S), (W / 2 - 110 * S, 920 * S)]
        d.polygon(ap, fill=(246, 240, 226, 255)); outline(d, ap, 7 * S)
        d.rectangle([W / 2 - 60 * S, 760 * S, W / 2 + 60 * S, 800 * S], outline=(200, 190, 170, 255), width=4 * S)
    if sp.get('straps'):
        d.polygon([(W / 2 - 100 * S, 615 * S), (W / 2 + 100 * S, 615 * S), (W / 2 + 40 * S, 690 * S), (W / 2 - 40 * S, 690 * S)],
                  fill=sp['shirt'] + (255,))
        for xs in (-70, 70):
            d.rectangle([W / 2 + xs * S - 14 * S, 620 * S, W / 2 + xs * S + 14 * S, 760 * S], fill=(40, 60, 120, 255))
            d.ellipse([W / 2 + xs * S - 10 * S, 745 * S, W / 2 + xs * S + 10 * S, 765 * S], fill=(230, 200, 90, 255))
    if sp.get('collar'):
        d.polygon([(W / 2 - 50 * S, 612 * S), (W / 2, 690 * S), (W / 2 + 50 * S, 612 * S)], fill=(245, 245, 240, 255))
        d.polygon([(W / 2 - 14 * S, 640 * S), (W / 2 + 14 * S, 640 * S), (W / 2, 670 * S)], fill=(150, 30, 30, 255))
    outline(d, body, 12 * S)
    # arms on top of body
    for sx in (-1, 1):
        x0 = W / 2 + sx * 120 * S
        end = hands[sx]
        mid = ((x0 + end[0]) / 2 + sx * 30 * S, (sh_y + end[1]) / 2 + 20 * S)
        d.line([(x0, sh_y), mid, end], fill=INK, width=14 * S, joint='curve')
        d.ellipse([end[0] - 24 * S, end[1] - 24 * S, end[0] + 24 * S, end[1] + 24 * S], fill=INK)
    if arms == 'bag':
        e = hands[1]
        d.rounded_rectangle([e[0] - 70 * S, e[1] + 10 * S, e[0] + 70 * S, e[1] + 110 * S], radius=16 * S, fill=(80, 46, 30, 255),
                            outline=INK, width=8 * S)
        d.arc([e[0] - 30 * S, e[1] - 20 * S, e[0] + 30 * S, e[1] + 30 * S], 180, 360, fill=INK, width=8 * S)
    if arms == 'stir':
        e = hands[1]
        d.line([(e[0] - 40 * S, e[1] - 180 * S), (e[0] + 60 * S, e[1] + 260 * S)], fill=(150, 100, 60, 255), width=18 * S)
        d.line([(e[0] - 40 * S, e[1] - 180 * S), (e[0] + 60 * S, e[1] + 260 * S)], fill=INK, width=4 * S)
    # head
    if sp['hat'] == 'bonnet':
        d = _hat(img, d, 'bonnet', hx, hy, hr)
    headcol = {'sick': (150, 210, 120), 'angry': (176, 120, 214)}.get(expr, (255, 255, 255))
    head = wobble_poly(hx, hy, hr, hr * 0.97, seed + 20, 56, 0.025)
    d.polygon(head, fill=headcol + (255,))
    hm = Image.new('L', (W, H), 0); ImageDraw.Draw(hm).polygon(head, fill=255)
    strokes(img, (hx - hr, hy - hr, hx + hr, hy + hr), [tuple(max(0, c - 22) for c in headcol)], 120, seed, (14 * S, 40 * S), 90, mask=hm)
    d = ImageDraw.Draw(img)
    outline(d, head, 15 * S)
    if sp['hat'] == 'bonnet':
        d.arc([hx - hr * 1.05, hy - hr * 1.05, hx + hr * 1.05, hy + hr * 0.9], 190, 350, fill=(120, 170, 210, 255), width=26 * S)
        d.line([(hx - hr * 0.7, hy + hr * 0.75), (hx - hr * 0.3, hy + hr * 1.05)], fill=(150, 196, 232, 255), width=12 * S)
        d.line([(hx + hr * 0.7, hy + hr * 0.75), (hx + hr * 0.3, hy + hr * 1.05)], fill=(150, 196, 232, 255), width=12 * S)
    if sp.get('bald'):
        for sx in (-1, 1):
            d.chord([hx + sx * hr * 0.98 - 50 * S, hy - 60 * S, hx + sx * hr * 0.98 + 50 * S, hy + 70 * S], 0, 360,
                    fill=(200, 200, 200, 255), outline=INK, width=6 * S)
    if sp.get('beard'):
        bd = [(hx - hr * 0.75, hy + hr * 0.2), (hx - hr * 0.55, hy + hr * 0.95), (hx, hy + hr * 1.18),
              (hx + hr * 0.55, hy + hr * 0.95), (hx + hr * 0.75, hy + hr * 0.2), (hx + hr * 0.4, hy + hr * 0.62),
              (hx - hr * 0.4, hy + hr * 0.62)]
        d.polygon(bd, fill=sp['beard'] + (255,)); outline(d, bd, 9 * S)
    # face
    ey = hy - 10 * S; ex = 72 * S
    brow = {'neutral': (0, 0), 'smug': (-14, 10), 'laugh': (-18, 8), 'angry': (30, 0), 'surprised': (-26, -30),
            'worried': (-26, -8), 'sad': (-22, 0), 'happy': (-10, -10), 'chew': (-8, -6), 'squint': (22, 10),
            'yawn': (-20, -14), 'sick': (-24, -4), 'think': (16, -14)}[expr]
    for sx in (-1, 1):
        bx = hx + sx * ex; tilt = brow[0] * S; by = ey - 70 * S + brow[1] * S
        if expr == 'think' and sx == 1:
            tilt = -tilt
        d.line([(bx - sx * 45 * S, by + tilt), (bx + sx * 45 * S, by - tilt * 0.3)], fill=INK, width=20 * S)
        if blink or expr == 'yawn':
            d.line([(bx - 22 * S, ey), (bx + 22 * S, ey)], fill=INK, width=9 * S)
        elif expr in ('surprised', 'worried', 'sick'):
            rr = 40 * S if expr == 'surprised' else 30 * S
            d.ellipse([bx - rr, ey - rr, bx + rr, ey + rr], fill=(255, 255, 255, 255), outline=INK, width=8 * S)
            d.ellipse([bx - 12 * S, ey - 12 * S + (10 * S if expr == 'sick' else 0), bx + 12 * S, ey + 12 * S + (10 * S if expr == 'sick' else 0)], fill=INK)
        elif expr in ('laugh', 'happy', 'chew'):
            d.arc([bx - 28 * S, ey - 10 * S, bx + 28 * S, ey + 34 * S], 200, 340, fill=INK, width=10 * S)
        elif expr == 'squint':
            d.line([(bx - 26 * S, ey), (bx + 26 * S, ey + (6 * S if sx < 0 else -6 * S))], fill=INK, width=10 * S)
        else:
            d.ellipse([bx - 15 * S, ey - 15 * S, bx + 15 * S, ey + 15 * S], fill=INK)
        if sp.get('glasses'):
            d.ellipse([bx - 44 * S, ey - 40 * S, bx + 44 * S, ey + 40 * S], outline=INK, width=7 * S)
        if sp.get('monocle') and sx == 1:
            d.ellipse([bx - 46 * S, ey - 44 * S, bx + 46 * S, ey + 44 * S], outline=(200, 170, 60, 255), width=8 * S)
            d.line([(bx + 40 * S, ey + 30 * S), (bx + 70 * S, ey + 200 * S)], fill=(200, 170, 60, 255), width=4 * S)
    if sp.get('glasses'):
        d.line([(hx - 28 * S, ey - 4 * S), (hx + 28 * S, ey - 4 * S)], fill=INK, width=7 * S)
    my = hy + 95 * S
    if sp.get('moustache'):
        d.polygon([(hx - 80 * S, my - 20 * S), (hx, my - 46 * S), (hx + 80 * S, my - 20 * S), (hx + 40 * S, my - 30 * S),
                   (hx, my - 26 * S), (hx - 40 * S, my - 30 * S)], fill=INK)
    if expr == 'laugh':
        d.chord([hx - 85 * S, my - 50 * S, hx + 85 * S, my + 60 * S], 0, 180, fill=INK)
        d.chord([hx - 50 * S, my + 10 * S, hx + 50 * S, my + 55 * S], 0, 180, fill=(220, 70, 80, 255))
    elif expr in ('smug', 'happy'):
        d.arc([hx - 70 * S, my - 50 * S, hx + 70 * S, my + 20 * S], 20, 160, fill=INK, width=11 * S)
    elif expr == 'surprised':
        d.ellipse([hx - 28 * S, my - 22 * S, hx + 28 * S, my + 36 * S], fill=INK)
    elif expr in ('worried', 'sad'):
        d.arc([hx - 60 * S, my - 6 * S, hx + 60 * S, my + 50 * S], 200, 340, fill=INK, width=11 * S)
    elif expr == 'chew':
        k = 1 if frame % 2 else 0
        # puffed cheeks
        for sx in (-1, 1):
            d.arc([hx + sx * 110 * S - 50 * S, my - 60 * S, hx + sx * 110 * S + 50 * S, my + 30 * S], 200 if sx < 0 else -20,
                  340 if sx < 0 else 160, fill=INK, width=6 * S)
        pts = [(hx - 60 * S + i * 20 * S, my + (10 if (i + k) % 2 else -10) * S) for i in range(7)]
        d.line(pts, fill=INK, width=10 * S, joint='curve')
    elif expr == 'yawn':
        d.ellipse([hx - 55 * S, my - 50 * S, hx + 55 * S, my + 90 * S], fill=INK)
        d.ellipse([hx - 30 * S, my + 30 * S, hx + 30 * S, my + 80 * S], fill=(220, 70, 80, 255))
    elif expr == 'sick':
        pts = [(hx - 70 * S + i * 23 * S, my + (12 if i % 2 else -6) * S) for i in range(7)]
        d.line(pts, fill=INK, width=10 * S, joint='curve')
        d.ellipse([hx + 90 * S, ey - 120 * S, hx + 120 * S, ey - 70 * S], fill=(140, 200, 255, 255), outline=INK, width=4 * S)
    elif expr == 'squint':
        d.line([(hx - 50 * S, my + 6 * S), (hx + 50 * S, my - 6 * S)], fill=INK, width=11 * S)
    elif expr == 'think':
        d.line([(hx - 40 * S, my + 10 * S), (hx + 30 * S, my)], fill=INK, width=11 * S)
    elif expr == 'angry':
        box = [hx - 80 * S, my - 30 * S, hx + 80 * S, my + 30 * S]
        d.rounded_rectangle(box, radius=10 * S, fill=(255, 255, 255, 255), outline=INK, width=9 * S)
        for i in range(1, 5):
            x = box[0] + i * (box[2] - box[0]) / 5; d.line([(x, box[1]), (x, box[3])], fill=INK, width=5 * S)
    else:
        d.line([(hx - 55 * S, my), (hx + 55 * S, my)], fill=INK, width=11 * S)
    if sp['hat'] and sp['hat'] != 'bonnet':
        d = _hat(img, d, sp['hat'], hx, hy, hr)
    # held props
    if prop == 'chunk' and arms in ('eat', 'hold'):
        c = make_chunk(1, 140 * S)
        e = hands[1]
        img.alpha_composite(c, (int(e[0] - c.width / 2), int(e[1] - c.height * 0.7)))
    if arms == 'magnify':
        e = hands[1]
        d.line([e, (e[0] + 50 * S, e[1] - 80 * S)], fill=(90, 60, 40, 255), width=16 * S)
        d.ellipse([e[0] + 0 * S, e[1] - 230 * S, e[0] + 140 * S, e[1] - 90 * S], fill=(200, 230, 255, 160), outline=INK, width=10 * S)
    return shrink(img, S)


# ------------------------------------------------------------- meat & props
def make_chunk(seed, size=200):
    r = rng(seed)
    W = H = size
    img = Image.new('RGBA', (W * 2, H * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    poly = wobble_poly(W, H, W * 0.8 * r.uniform(0.75, 1.0), H * 0.6 * r.uniform(0.7, 1.0), seed, 18, 0.12)
    d.polygon(poly, fill=(196, 44, 52, 255))
    m = Image.new('L', img.size, 0); ImageDraw.Draw(m).polygon(poly, fill=255)
    strokes(img, (0, 0, W * 2, H * 2), [(150, 26, 40), (226, 90, 96), (240, 170, 170)], 80, seed, (W * 0.1, W * 0.3), 220, mask=m)
    d = ImageDraw.Draw(img)
    # fat marbling
    for k in range(3):
        y = H * (0.7 + 0.25 * k)
        d.arc([W * 0.4, y - H * 0.2, W * 1.6, y + H * 0.2], 200, 330, fill=(250, 230, 220, 255), width=max(3, W // 20))
    d.ellipse([W * 0.6, H * 0.6, W * 0.85, H * 0.8], fill=(255, 210, 210, 255))
    outline(d, poly, max(6, W // 9))
    return img.resize((W, H), Image.LANCZOS)


def make_cookie(size=300):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = size / 2; R = size * 0.42
    d.ellipse([c - R, c - R * 0.9, c + R, c + R * 0.9], fill=(214, 160, 90, 255), outline=INK, width=10)
    r = rng(4)
    for k in range(8):
        x = c + r.uniform(-R * 0.6, R * 0.6); y = c + r.uniform(-R * 0.5, R * 0.5)
        d.ellipse([x - 14, y - 10, x + 14, y + 10], fill=(80, 46, 30, 255))
    return img


def make_vulture(kind='fly', wing=0, fat=False, eye='normal', vomit=0.0, napkin=False):
    """Side view vulture facing right. kind: fly | perch."""
    W, H = 1000 * S, 1300 * S
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy = W * 0.56, H * 0.6
    bw = 260 * S * (1.35 if fat else 1.0); bh = 140 * S * (1.6 if fat else 1.0)
    # far wing
    def wingpoly(sign, up):
        base = [(80, -40), (20, -280), (-120, -430), (-210, -410), (-175, -335), (-265, -320), (-215, -250), (-295, -225),
                (-205, -160), (-110, -60)]
        base = [(x * 1.7, y * 1.7) for x, y in base]
        if up:
            return [(cx + x * S, cy + y * S) for x, y in base]
        return [(cx + x * S, cy - 40 * S + (-(y + 40)) * S * 0.75) for x, y in base]
    if kind == 'fly':
        wp = wingpoly(1, wing == 0)
        d.polygon(wp, fill=(52, 40, 40, 255)); outline(d, wp, 10 * S)
        for k in (3, 5, 7):
            d.line([wp[k], ((wp[k][0] + cx) / 2, (wp[k][1] + cy) / 2)], fill=(150, 130, 120, 255), width=6 * S)
    # tail
    d.polygon([(cx - bw * 0.8, cy), (cx - bw * 1.4, cy + 40 * S), (cx - bw * 1.35, cy - 30 * S)], fill=(40, 32, 32, 255), outline=INK)
    body = wobble_poly(cx, cy, bw, bh, 7, 40, 0.03)
    d.polygon(body, fill=(64, 50, 48, 255))
    bm = Image.new('L', (W, H), 0); ImageDraw.Draw(bm).polygon(body, fill=255)
    strokes(img, (cx - bw, cy - bh, cx + bw, cy + bh), [(44, 34, 34), (96, 80, 74)], 200, 5, (14 * S, 36 * S), 200, angle=0.1, mask=bm)
    d = ImageDraw.Draw(img); outline(d, body, 12 * S)
    # ruff
    d.ellipse([cx + bw * 0.55, cy - bh * 0.7, cx + bw * 0.95, cy - bh * 0.1], fill=(230, 222, 210, 255), outline=INK, width=8 * S)
    # neck + head
    hx, hy = cx + bw * 1.0, cy - bh * 0.85
    d.line([(cx + bw * 0.75, cy - bh * 0.4), (hx, hy)], fill=(200, 80, 80, 255), width=40 * S)
    d.ellipse([hx - 70 * S, hy - 60 * S, hx + 70 * S, hy + 60 * S], fill=(212, 86, 86, 255), outline=INK, width=9 * S)
    # beak
    open_ = vomit > 0
    if open_:
        d.polygon([(hx + 50 * S, hy - 20 * S), (hx + 150 * S, hy - 10 * S), (hx + 130 * S, hy + 20 * S), (hx + 60 * S, hy)],
                  fill=(236, 220, 180, 255), outline=INK)
        d.polygon([(hx + 50 * S, hy + 20 * S), (hx + 130 * S, hy + 60 * S), (hx + 60 * S, hy + 50 * S)], fill=(236, 220, 180, 255),
                  outline=INK)
    else:
        bk = [(hx + 50 * S, hy - 22 * S), (hx + 140 * S, hy - 8 * S), (hx + 150 * S, hy + 30 * S), (hx + 125 * S, hy + 12 * S),
              (hx + 55 * S, hy + 22 * S)]
        d.polygon(bk, fill=(236, 220, 180, 255)); outline(d, bk, 7 * S)
    # eye
    if eye == 'scared':
        d.ellipse([hx - 10 * S, hy - 50 * S, hx + 50 * S, hy + 10 * S], fill=(255, 255, 255, 255), outline=INK, width=6 * S)
        d.ellipse([hx + 14 * S, hy - 28 * S, hx + 30 * S, hy - 12 * S], fill=INK)
    elif eye == 'happy':
        d.arc([hx - 5 * S, hy - 40 * S, hx + 45 * S, hy], 200, 340, fill=INK, width=8 * S)
    else:
        d.ellipse([hx + 6 * S, hy - 30 * S, hx + 30 * S, hy - 6 * S], fill=INK)
        d.line([(hx - 10 * S, hy - 46 * S), (hx + 44 * S, hy - 36 * S)], fill=INK, width=9 * S)
    if napkin:
        nk = [(hx - 20 * S, hy + 50 * S), (hx + 80 * S, hy + 45 * S), (hx + 40 * S, hy + 160 * S)]
        d.polygon(nk, fill=(250, 250, 250, 255)); outline(d, nk, 6 * S)
        for k in range(3):
            d.line([(hx + k * 25 * S, hy + 60 * S), (hx + 20 * S + k * 10 * S, hy + 130 * S)], fill=(220, 60, 60, 255), width=4 * S)
    # legs
    if kind == 'perch':
        for k in (-1, 1):
            x = cx + k * 50 * S
            d.line([(x, cy + bh * 0.9), (x, cy + bh + 120 * S)], fill=(220, 200, 180, 255), width=12 * S)
            d.line([(x - 30 * S, cy + bh + 120 * S), (x + 40 * S, cy + bh + 120 * S)], fill=INK, width=12 * S)
    else:
        d.line([(cx - 40 * S, cy + bh * 0.85), (cx - 120 * S, cy + bh * 1.1)], fill=(220, 200, 180, 255), width=10 * S)
    if kind == 'fly':
        wp = wingpoly(1, wing == 1)
        wp = [(x + 40 * S, y + 20 * S) for x, y in wp]
        d.polygon(wp, fill=(70, 56, 52, 255)); outline(d, wp, 10 * S)
        for k in (3, 5, 7):
            d.line([wp[k], ((wp[k][0] + cx) / 2, (wp[k][1] + cy) / 2)], fill=(150, 130, 120, 255), width=6 * S)
    return shrink(img, S)


def make_bubble(content, W=700, H=560):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cloud = wobble_poly(W / 2, H * 0.42, W * 0.44, H * 0.36, 3, 30, 0.08)
    d.polygon(cloud, fill=(255, 255, 255, 255)); outline(d, cloud, 12)
    for (x, y, r) in [(W * 0.2, H * 0.84, 34), (W * 0.12, H * 0.95, 18)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, 255), outline=INK, width=8)
    c = content.resize((int(W * 0.56), int(W * 0.56 * content.height / content.width)), Image.LANCZOS)
    img.alpha_composite(c, (int(W / 2 - c.width / 2), int(H * 0.42 - c.height / 2)))
    return img


def make_sheep(W=600, H=450):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x in (0.3, 0.45, 0.62):
        d.line([(W * x, H * 0.6), (W * x, H * 0.95)], fill=INK, width=16)
    wool = wobble_poly(W * 0.45, H * 0.45, W * 0.33, H * 0.28, 2, 30, 0.12)
    d.polygon(wool, fill=(250, 248, 240, 255)); outline(d, wool, 12)
    d.ellipse([W * 0.68, H * 0.25, W * 0.92, H * 0.55], fill=(60, 56, 60, 255), outline=INK, width=8)
    d.ellipse([W * 0.8, H * 0.33, W * 0.84, H * 0.38], fill=(255, 255, 255, 255))
    return img


def make_deer(W=600, H=520):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for x in (0.28, 0.38, 0.58, 0.66):
        d.line([(W * x, H * 0.6), (W * x, H * 0.97)], fill=INK, width=14)
    body = wobble_poly(W * 0.47, H * 0.52, W * 0.28, H * 0.15, 4, 30, 0.04)
    d.polygon(body, fill=(186, 120, 66, 255)); outline(d, body, 10)
    d.line([(W * 0.68, H * 0.45), (W * 0.78, H * 0.25)], fill=(186, 120, 66, 255), width=40)
    d.ellipse([W * 0.72, H * 0.14, W * 0.9, H * 0.3], fill=(186, 120, 66, 255), outline=INK, width=8)
    for sx in (-1, 1):
        x = W * 0.8 + sx * 20
        d.line([(x, H * 0.16), (x + sx * 40, H * 0.0 + 10), (x + sx * 70, H * 0.04)], fill=(110, 70, 40, 255), width=10, joint='curve')
    d.ellipse([W * 0.82, H * 0.19, W * 0.85, H * 0.22], fill=INK)
    return img


def make_paper(lines, sub, seed=1, W=900, H=640):
    img = Image.new('RGBA', (W, H), (238, 228, 200, 255))
    strokes(img, (0, 0, W, H), [(226, 214, 184), (244, 236, 212)], 600, seed, (20, 50), 160, angle=0)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=12)
    d.text((W / 2, 40), sub, font=font(46), fill=INK, anchor='mt')
    d.line([(40, 110), (W - 40, 110)], fill=INK, width=6)
    y = 140
    for ln in lines:
        d.text((W / 2, y), ln, font=font(108), fill=(170, 30, 30, 255), anchor='mt'); y += 120
    for i in range(4):
        d.line([(50, y + 30 + i * 36), (W - 50, y + 30 + i * 36)], fill=(130, 120, 100, 255), width=12)
    return img


def make_forecast(W=1000, H=800):
    img = A.wood_board(W, H, 5, (70, 110, 150)); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=16)
    d.text((W / 2, 50), 'PRONÓSTICO', font=font(110), fill=(255, 240, 200, 255), anchor='mt', stroke_width=8, stroke_fill=INK)
    d.text((W / 2, 190), 'MAÑANA:', font=font(70), fill=(255, 255, 255, 255), anchor='mt', stroke_width=6, stroke_fill=INK)
    # cloud + chops
    cl = wobble_poly(W / 2, 400, 230, 90, 2, 30, 0.1)
    d.polygon(cl, fill=(250, 250, 250, 255)); outline(d, cl, 10)
    for k, x in enumerate((0.35, 0.5, 0.65)):
        ch = make_chop(150).rotate(-20 + k * 20, expand=True)
        img.alpha_composite(ch, (int(W * x - ch.width / 2), 470))
    d.text((W / 2, 680), 'NUBLADO CON CHULETAS', font=font(62), fill=(255, 220, 120, 255), anchor='mt', stroke_width=6, stroke_fill=INK)
    return img


def make_chop(size=200):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    s = size
    d.line([(s * 0.55, s * 0.5), (s * 0.95, s * 0.1)], fill=(250, 244, 230, 255), width=int(s * 0.12))
    d.line([(s * 0.55, s * 0.5), (s * 0.95, s * 0.1)], fill=INK, width=3)
    d.ellipse([s * 0.05, s * 0.3, s * 0.65, s * 0.9], fill=(200, 50, 56, 255), outline=INK, width=6)
    d.arc([s * 0.12, s * 0.38, s * 0.58, s * 0.84], 120, 300, fill=(250, 236, 220, 255), width=8)
    return img


def make_sign(text, col=(255, 230, 120), W=900, H=360):
    img = A.wood_board(W, H, 9); d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=INK, width=14)
    d.text((W / 2, H / 2), text, font=font(150), fill=col + (255,), anchor='mm', stroke_width=10, stroke_fill=INK)
    return img


def make_kettle(W=700, H=700):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    # tripod
    d.line([(W * 0.2, H * 0.98), (W * 0.5, H * 0.05)], fill=(90, 60, 40, 255), width=20)
    d.line([(W * 0.8, H * 0.98), (W * 0.5, H * 0.05)], fill=(90, 60, 40, 255), width=20)
    d.line([(W * 0.5, H * 0.05), (W * 0.5, H * 0.3)], fill=INK, width=8)
    pot = wobble_poly(W * 0.5, H * 0.55, W * 0.3, H * 0.22, 3, 30, 0.02)
    pot = [p for p in pot if p[1] > H * 0.42] + [(W * 0.2, H * 0.42)]
    d.polygon(pot, fill=(40, 38, 44, 255)); outline(d, pot, 10)
    d.ellipse([W * 0.2, H * 0.36, W * 0.8, H * 0.48], fill=(240, 226, 170, 255), outline=INK, width=10)
    for k in range(5):
        x = W * (0.3 + k * 0.1); d.ellipse([x - 16, H * 0.4 - 12, x + 16, H * 0.4 + 12], fill=(255, 250, 220, 255), outline=(150, 130, 80, 255), width=3)
    for k in range(5):
        x = W * (0.32 + k * 0.09)
        d.polygon([(x - 34, H * 0.97), (x, H * 0.8), (x + 34, H * 0.97)], fill=(255, 130, 20, 255))
        d.polygon([(x - 15, H * 0.97), (x, H * 0.88), (x + 15, H * 0.97)], fill=(255, 230, 120, 255))
    return img


def make_bench(W=1400, H=500):
    img = A.wood_board(W, H, 6, (140, 92, 54))
    a = Image.new('L', (W, H), 0); ad = ImageDraw.Draw(a)
    ad.rectangle([0, H * 0.35, W, H * 0.55], fill=255)
    for x in (0.06, 0.94):
        ad.rectangle([W * x - 25, H * 0.35, W * x + 25, H], fill=255)
    img.putalpha(a)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H * 0.35, W - 1, H * 0.55], outline=INK, width=8)
    return img


def make_easel(sign):
    W, H = sign.width, int(sign.height * 2.2)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.line([(W * 0.2, H), (W * 0.45, sign.height * 0.5)], fill=(110, 70, 40, 255), width=24)
    d.line([(W * 0.8, H), (W * 0.55, sign.height * 0.5)], fill=(110, 70, 40, 255), width=24)
    img.alpha_composite(sign, (0, int(sign.height * 0.3)))
    return img


def make_exclaim(S2=300):
    img = Image.new('RGBA', (S2, S2), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((S2 / 2, S2 / 2), '!', font=font(260), fill=(255, 220, 60, 255), anchor='mm', stroke_width=14, stroke_fill=INK)
    return img


def make_hills_sky(kind='day'):
    """Sky panorama with a painted band of hills at the horizon."""
    sky = A.make_sky(kind).convert('RGBA')
    W, H = sky.size
    hor = int((1.35 - 0.0) / 1.6 * (H - 1))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    r = rng(12)
    for layer, (col, amp, base) in enumerate([((128, 160, 140), 70, 0), ((96, 140, 84), 46, 0)]):
        pts = [(0, hor + 4)]
        for x in range(0, W + 40, 40):
            y = hor - base - amp * (0.55 + 0.45 * math.sin(x / W * 2 * math.pi * (5 + layer * 3) + layer * 2)) \
                - 18 * math.sin(x / 70 + layer)
            pts.append((x, y))
        pts.append((W, hor + 4))
        d.polygon(pts, fill=col + (255,))
        d.line(pts[1:-1], fill=(40, 60, 50, 255), width=4)
    strokes(lay, (0, hor - 140, W, hor), [(110, 150, 96), (150, 176, 120), (80, 120, 74)], 3000, 3, (10, 30), 160,
            angle=0.0, mask=lay.getchannel('A'))
    sky.alpha_composite(lay)
    return sky.convert('RGB')


if __name__ == '__main__':
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    os.makedirs(out, exist_ok=True)
    sheet = Image.new('RGBA', (640 * 7, 1100 * 2), (110, 170, 230, 255))
    cfg = [('crouch', 'surprised', 'stir', 'stand'), ('silas', 'chew', 'eat', 'stand'), ('ezra', 'squint', 'hold', 'stand'),
           ('doctor', 'think', 'bag', 'stand'), ('expert1', 'smug', 'magnify', 'stand'), ('expert2', 'happy', 'point', 'stand'),
           ('silas', 'sick', 'down', 'stand')]
    for i, (k, e, a, l) in enumerate(cfg):
        sheet.alpha_composite(make_char(k, e, a, l, prop='chunk'), (640 * i, 0))
    sheet.alpha_composite(make_char('ezra', 'yawn', 'yawn', 'sit'), (0, 1100))
    sheet.alpha_composite(make_char('silas', 'happy', 'runA', 'runA'), (640, 1100))
    sheet.alpha_composite(make_vulture('fly', 0, fat=True).resize((480, 624)), (1280, 1150))
    sheet.alpha_composite(make_vulture('fly', 1, vomit=1, eye='scared').resize((480, 624)), (1900, 1150))
    sheet.alpha_composite(make_vulture('perch', napkin=True, eye='happy').resize((480, 624)), (2520, 1150))
    sheet.alpha_composite(make_chunk(3, 200), (3200, 1200)); sheet.alpha_composite(make_cookie(200), (3420, 1200))
    sheet.alpha_composite(make_bubble(make_sheep()).resize((420, 336)), (3200, 1450))
    sheet.alpha_composite(make_forecast().resize((500, 400)), (3700, 1150))
    sheet.alpha_composite(make_kettle().resize((350, 350)), (3700, 1600))
    sheet.convert('RGB').resize((2240, 1100)).save(os.path.join(out, 'cast.jpg'), quality=85)
