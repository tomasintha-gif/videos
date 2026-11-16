"""Synthesize stems: out/music.wav and out/sfx.wav (48 kHz mono)."""
import json, os, math
import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
WJ = json.load(open(os.path.join(HERE, 'words.json')))
T, DUR = WJ['times'], WJ['duration']
N = int(DUR * SR) + SR
rs = np.random.RandomState(1)


def wt(i): return T[i][0]


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)


def tone(f, dur, kind='sine', a=0.005, r=0.3, vib=0.0):
    n = int(dur * SR); t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + vib * np.sin(2 * np.pi * 5.5 * t))) / SR
    if kind == 'sine': w = np.sin(ph)
    elif kind == 'saw': w = 2 * ((ph / (2 * np.pi)) % 1) - 1
    elif kind == 'square': w = np.sign(np.sin(ph)) * 0.7
    else: w = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    return w * env(n, a, r)


def lp(x, k=0.1):
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc); y[i] = acc
    return y


def lpf(x, cutoff):
    # fast one-pole via cumulative trick (vectorised approx using FFT)
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cutoff) ** 4)
    return np.fft.irfft(X, len(x))


def noise(dur):
    return rs.uniform(-1, 1, int(dur * SR))


def add(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf): return
    j = min(len(buf), i + len(sig)); buf[i:j] += sig[:j - i] * g


# ------------------------------------------------------------- music
music = np.zeros(N)
bpm = 116; beat = 60 / bpm
stop = wt(166) - 0.05          # twist line: music stops
prog = [(48, 52, 55), (53, 57, 60), (55, 59, 62), (48, 52, 55)]  # C F G C
mel = [72, 74, 76, 74, 72, 67, 69, 71, 72, 76, 79, 77, 76, 74, 72, 71]
kick = lpf(np.sin(2 * np.pi * np.cumsum(np.linspace(140, 45, int(0.18 * SR))) / SR) * env(int(0.18 * SR), 0.001, 0.08), 400)
snare = lpf(noise(0.15) * env(int(0.15 * SR), 0.001, 0.05), 5000) * 0.6
def mf(m): return 440 * 2 ** ((m - 69) / 12)
t = 0.0; b = 0
while t < stop:
    bar = (b // 4) % 4; chord = prog[bar]
    if b % 2 == 0: add(music, kick, t, 0.9)
    else: add(music, snare, t, 0.7)
    # plucked bass (oom-pah)
    root = chord[0] - 12 if b % 2 == 0 else chord[2] - 12
    add(music, tone(mf(root), beat * 0.9, 'harm', 0.003, 0.18), t, 0.5)
    # brass-ish pad on bar start
    if b % 4 == 0:
        for m in chord:
            add(music, lpf(tone(mf(m), beat * 4, 'saw', 0.06, 1.6), 1800), t, 0.08)
    # whistle melody (pizzicato) every half-beat
    for h in range(2):
        m = mel[(b * 2 + h) % len(mel)]
        if (b + h) % 3 != 2:
            add(music, tone(mf(m), beat * 0.45, 'sine', 0.002, 0.09), t + h * beat / 2, 0.22)
    t += beat; b += 1
# soft fade into stop + low drone after the stop
fade = int(0.08 * SR); i0 = int(stop * SR)
music[i0 - fade:i0] *= np.linspace(1, 0, fade); music[i0:] = 0
dr = lpf(tone(mf(36), DUR - stop + 0.5, 'saw', 0.4, 50) + tone(mf(43), DUR - stop + 0.5, 'saw', 0.4, 50) * 0.6, 300)
add(music, dr, stop, 0.5)

# ------------------------------------------------------------- sfx
sfx = np.zeros(N)
def splat(g=1.0, dur=0.12):
    n = noise(dur) * env(int(dur * SR), 0.001, 0.03)
    return lpf(n, 1400) * 2.0 * g + tone(rs.uniform(90, 140), dur, 'sine', 0.001, 0.04) * 0.6 * g
def whoosh(dur=0.6, g=1.0):
    n = noise(dur); k = np.sin(np.linspace(0, np.pi, len(n))) ** 2
    return lpf(n * k, 1200) * 1.6 * g
def ting(f=1760, g=1.0):
    return (tone(f, 0.6, 'sine', 0.001, 0.25) + 0.5 * tone(f * 2.01, 0.6, 'sine', 0.001, 0.15)) * g
def pop(g=1.0):
    n = int(0.08 * SR); f = np.linspace(500, 1400, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.03) * g
def thump(g=1.0):
    return lpf(tone(70, 0.15, 'sine', 0.001, 0.05) + noise(0.15) * env(int(0.15 * SR), 0.001, 0.02) * 0.3, 600) * g
def chomp():
    return np.concatenate([lpf(noise(0.06), 3000) * env(int(0.06 * SR), 0.001, 0.02), np.zeros(int(0.05 * SR)),
                           lpf(noise(0.07), 2500) * env(int(0.07 * SR), 0.001, 0.02)]) * 1.4
def baa():
    return lpf(tone(330, 0.6, 'saw', 0.02, 0.35, vib=0.06), 1500) * 0.5
def flap():
    return lpf(noise(0.09) * env(int(0.09 * SR), 0.005, 0.03), 900) * 1.5
def yawn():
    n = int(1.0 * SR); f = np.linspace(380, 180, n)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.linspace(0, np.pi, n)) * 0.5
    return lpf(w + noise(1.0) * 0.08 * np.sin(np.linspace(0, np.pi, n)), 1500)
def blargh():
    n = int(0.7 * SR); f = 110 + 30 * np.sin(np.linspace(0, 40, n))
    return lpf(np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * env(n, 0.01, 0.4) + noise(0.7) * 0.4 * env(n, 0.01, 0.3), 800) * 0.8
def sting():
    return (lpf(tone(55, 2.0, 'saw', 0.001, 0.9), 400) * 1.2 + tone(880, 2.0, 'sine', 0.001, 0.5) * 0.3 +
            tone(932, 2.0, 'sine', 0.001, 0.5) * 0.3)
def lowhit():
    return lpf(tone(40, 2.5, 'sine', 0.001, 0.8) * 1.5 + noise(2.5) * env(int(2.5 * SR), 0.001, 0.12) * 0.6, 300)
def bubbles(dur):
    out = np.zeros(int(dur * SR))
    for k in range(int(dur * 7)):
        n = int(0.05 * SR); f = np.linspace(rs.uniform(300, 500), rs.uniform(700, 1100), n)
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.02) * 0.25
        i = rs.randint(0, len(out) - n); out[i:i + n] += b
    return out
def birds(dur):
    out = np.zeros(int(dur * SR))
    for k in range(int(dur * 4)):
        n = int(0.12 * SR); f = 2600 + 900 * np.sin(np.linspace(0, 9, n))
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.005, 0.05) * 0.25
        i = rs.randint(0, len(out) - n); out[i:i + n] += b
    return out
def paper():
    return lpf(noise(0.35) * (0.5 + 0.5 * np.sin(np.linspace(0, 40, int(0.35 * SR)))) * env(int(0.35 * SR), 0.01, 0.2), 4000) * 0.8

# hook: sprinkle of splats + big one on "carne"
for k in range(14):
    add(sfx, splat(rs.uniform(0.4, 0.8)), rs.uniform(0.3, 3.6))
add(sfx, splat(1.6, 0.25), wt(13) + 0.02)
add(sfx, birds(1.5), wt(14))
add(sfx, bubbles(5.0), wt(18) - 0.1, 0.8)
for k in range(10):
    add(sfx, splat(rs.uniform(0.4, 0.8)), rs.uniform(wt(29), wt(34)))
add(sfx, whoosh(0.8), wt(34) - 0.2)
add(sfx, pop(0.8), wt(47) - 0.1); add(sfx, ting(2093, 0.5), wt(47))
for k in range(int((wt(52) - wt(48)) * 7)):
    add(sfx, thump(0.7), wt(48) + k / 7)
add(sfx, chomp(), wt(62) + 0.05)
add(sfx, baa(), wt(67)); add(sfx, ting(1568, 0.6), wt(70))
for k in range(3):
    add(sfx, paper(), wt(71) + 0.1 + k * 0.5)
add(sfx, ting(1760, 0.7), wt(85))
add(sfx, pop(), wt(91) - 0.1); add(sfx, pop(), wt(95) - 0.1)
add(sfx, whoosh(0.7, 0.8), wt(101))
add(sfx, sting(), wt(117) - 0.02, 0.8)
add(sfx, whoosh(0.5, 1.0), wt(119) - 0.15)  # flash into explanation
for k in range(int((wt(129) - wt(124)) * 7)):
    add(sfx, flap(), wt(124) + k / 7)
add(sfx, ting(2349, 0.7), wt(132)); add(sfx, blargh(), wt(133)); add(sfx, whoosh(0.8, 0.8), wt(136))
for k in range(7):
    add(sfx, splat(0.7), wt(139) + 0.1 + 0.4 + k * 0.32)
add(sfx, yawn(), wt(150)); add(sfx, yawn(), wt(152), 0.8); add(sfx, yawn(), wt(152) + 0.4, 0.7)
for k in range(40):
    add(sfx, splat(rs.uniform(0.3, 0.7)), rs.uniform(wt(156) + 0.6, wt(166) - 0.2))
for k in range(6):
    add(sfx, chomp() * 0.5, wt(166) + 0.3 + k * 0.45)
add(sfx, lowhit(), wt(181))

os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
L = int(DUR * SR)
sf.write(os.path.join(HERE, 'out', 'music.wav'), music[:L].astype(np.float32), SR)
sf.write(os.path.join(HERE, 'out', 'sfx.wav'), sfx[:L].astype(np.float32), SR)
print('stems written', L / SR)
