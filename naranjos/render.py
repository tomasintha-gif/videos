"""Render the short: python3 render.py [--preview] [--frames a:b] [--only shot]"""
import os, sys, json, math, re, subprocess, time
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from multiprocessing import Pool

import scenes as SC
import world as Wd
import assets as A
from engine import render as eng_render

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
RW, RH = 720, 1280
OW, OH = 1080, 1920
XF = 0.15  # half crossfade


def load_times():
    p = os.path.join(HERE, 'words.json')
    if os.path.exists(p):
        return [tuple(x) for x in json.load(open(p))]
    return SC.estimate_times(SC.WORDS)


TIMES = load_times()
AUDIO_END = TIMES[-1][1]
STARTS = [0.0] + [max(0.0, TIMES[i][0] - 0.08) for i in SC.SHOT_START[1:]]
ENDS = STARTS[1:] + [AUDIO_END + 0.05]
TOTAL = ENDS[-1]


def shot_events(i):
    ev = {}
    for k, wi in SC.EVENTS.items():
        tt = TIMES[wi][0]
        if STARTS[i] <= tt < ENDS[i]:
            ev[k] = tt - STARTS[i]
    return ev


EVS = [shot_events(i) for i in range(len(SC.SHOTS))]
L = None


def init():
    global L
    L = Wd.Lib()


def render_shot(i, T):
    d = ENDS[i] - STARTS[i]
    t = T - STARTS[i]
    cam, items, em, sky, fogc, grade, tint = SC.SHOTS[i](L, t, d, EVS[i])
    pt = (0.74, 0.8, 0.98) if sky == 'night' else ((1.0, 0.92, 0.88) if sky == 'dawn' and grade is Wd.grade_dusk else None)
    if pt is None:
        for it in items:
            it.pop('post', None)
    fr = eng_render(cam, L.worlds[sky], items, fogc, grade=grade, ground_tint=tint, emissive=em, post_tint=pt)
    return np.clip(fr, 0, 255)


def smear(fr, s, axis):
    if s <= 0.01:
        return fr
    n = 7; L_ = int(70 * s)
    acc = np.zeros_like(fr)
    for k in range(n):
        off = int((k / (n - 1) - 0.5) * L_)
        acc += np.roll(fr, off, axis=axis)
    return acc / n


def frame_at(T):
    i = max(j for j in range(len(STARTS)) if STARTS[j] <= T) if T >= 0 else 0
    fr = render_shot(i, T)
    # crossfade + whip smear around boundaries
    for b in (i, i + 1):
        if 0 < b < len(STARTS):
            B = STARTS[b]
            if abs(T - B) < XF:
                other = b - 1 if b == i else b
                fo = render_shot(other, T)
                a = (T - (B - XF)) / (2 * XF)  # weight of shot b
                if other == b:
                    fr = fr * (1 - a) + fo * a
                else:
                    fr = fo * (1 - a) + fr * a
                s = 1 - abs(T - B) / XF
                fr = smear(fr, s, 1 if b % 2 else 0)
    return fr


SUB_FONT = None


def subtitle(img, T):
    global SUB_FONT
    if SUB_FONT is None:
        SUB_FONT = A.font(112)
    idx = None
    for k, (s, e) in enumerate(TIMES):
        nxt = TIMES[k + 1][0] if k + 1 < len(TIMES) else e + 0.4
        if s <= T < max(nxt, s + 0.05):
            idx = k; break
    if idx is None:
        return img
    w = SC.WORDS[idx]
    txt = re.sub(r'[^\wáéíóúÁÉÍÓÚñÑüÜ°\-]', '', w)
    # join tiny words with the next one when it is short (e.g. "a la")
    if not txt:
        return img
    age = T - TIMES[idx][0]
    sc = 1.0 + 0.12 * max(0, 1 - age / 0.09)
    f = A.font(int(112 * sc))
    d = ImageDraw.Draw(img)
    cx, cy = OW / 2, OH * 0.70
    d.text((cx + 6, cy + 8), txt, font=f, fill=(0, 0, 0, 160), anchor='mm', stroke_width=8, stroke_fill=(0, 0, 0, 160))
    d.text((cx, cy), txt, font=f, fill=(255, 255, 255), anchor='mm', stroke_width=7, stroke_fill=(10, 10, 12))
    return img


GRAIN = None


def finish(fr, T):
    global GRAIN
    img = Image.fromarray(fr.astype(np.uint8)).resize((OW, OH), Image.BICUBIC)
    if GRAIN is None:
        rs = np.random.RandomState(0)
        g = rs.normal(0, 5, (OH // 4, OW // 4)).astype(np.float32)
        GRAIN = np.asarray(Image.fromarray(g).resize((OW, OH), Image.BICUBIC))[..., None]
    a = np.asarray(img, np.float32) + GRAIN
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return subtitle(img, T)


def work(args):
    f0, f1, outdir = args
    for f in range(f0, f1):
        T = f / FPS
        img = finish(frame_at(T), T)
        img.save(os.path.join(outdir, f'f{f:05d}.jpg'), quality=93)
    return f1 - f0


def main():
    outdir = os.path.join(HERE, 'out', 'frames'); os.makedirs(outdir, exist_ok=True)
    nfr = int(math.ceil(TOTAL * FPS))
    rng = (0, nfr)
    for a in sys.argv[1:]:
        if a.startswith('--frames'):
            x, y = a.split('=')[1].split(':'); rng = (int(x), int(y))
    chunks = []
    step = 12
    for f in range(rng[0], rng[1], step):
        chunks.append((f, min(rng[1], f + step), outdir))
    t0 = time.time()
    with Pool(os.cpu_count(), initializer=init) as p:
        done = 0
        for n in p.imap_unordered(work, chunks):
            done += n
            if done % 120 < step:
                print(f'{done}/{rng[1] - rng[0]} frames  {time.time() - t0:.0f}s', flush=True)
    print('rendered', time.time() - t0)
    if '--noencode' in sys.argv:
        return
    voice = os.path.join(HERE, 'voice.mp3')
    out = os.path.join(HERE, 'out', 'naranjos.mp4')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(outdir, 'f%05d.jpg')]
    if os.path.exists(voice):
        cmd += ['-i', voice, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest']
    else:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-shortest']
    cmd += ['-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-color_range', 'tv',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', out]
    subprocess.run(cmd, check=True)
    print('wrote', out)


if __name__ == '__main__':
    main()
