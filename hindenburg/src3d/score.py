"""Synthesised score + SFX for the 3D Hindenburg short. Usage: python3 score.py out.wav [timings.json]"""
import json, sys, wave, pathlib
import numpy as np

SR = 48000
SHOTS = [0, 3.5, 7.5, 12, 16, 20.5, 25.5, 32, 37.5, 40.5, 45, 48, 52]
if len(sys.argv) > 2 and pathlib.Path(sys.argv[2]).exists():
    SHOTS = json.loads(pathlib.Path(sys.argv[2]).read_text()).get('shots', SHOTS)
DUR = SHOTS[-1]
N = int(DUR * SR)
rng = np.random.default_rng(7)
t = np.arange(N) / SR
L = np.zeros(N); R = np.zeros(N)

def add(sig, start, gain=1.0, pan=0.0):
    i = int(start * SR); j = min(N, i + len(sig))
    if i >= N or j <= i: return
    s = sig[: j - i] * gain
    L[i:j] += s * (1 - max(0, pan)); R[i:j] += s * (1 + min(0, pan))

def env(n, a=0.01, r=0.3):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e

def lowpass(x, k):  # one-pole, k in (0,1)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)): acc += k * (x[i] - acc); y[i] = acc
    return y

def fast_lp(x, cutoff):  # FFT brick-wall-ish lowpass
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[f > cutoff] *= np.exp(-(f[f > cutoff] - cutoff) / (cutoff * 0.3)); return np.fft.irfft(X, len(x))

def bandnoise(n, lo, hi):
    X = np.fft.rfft(rng.standard_normal(n)); f = np.fft.rfftfreq(n, 1 / SR); X[(f < lo) | (f > hi)] = 0; y = np.fft.irfft(X, n); return y / (np.abs(y).max() + 1e-9)

# --- bed: minor drone (D) with slow swells, darker after the fire ---
notes = [36.71, 55.0, 73.42, 87.31]  # D1 A1 D2 F2
bed = sum(np.sin(2 * np.pi * f * t + i) * (0.5 if i else 1.0) for i, f in enumerate(notes))
bed *= 0.55 + 0.45 * np.sin(2 * np.pi * t / 7.3) ** 2
bed += bandnoise(N, 60, 400) * 0.25
bed = bed / np.abs(bed).max() * 0.16
bed *= np.clip(t / 1.5, 0, 1) * np.clip((DUR - t) / 0.6, 0, 1)
add(bed, 0)

# --- pulse: soft tick on beats at 96 bpm, from shot 2 to the investigation ---
beat = 60 / 96
for k in np.arange(SHOTS[1], SHOTS[9], beat):
    n = int(0.09 * SR); tick = np.sin(2 * np.pi * 220 * np.arange(n) / SR) * np.exp(-np.arange(n) / (0.015 * SR)) + bandnoise(n, 3000, 9000) * 0.3 * np.exp(-np.arange(n) / (0.01 * SR))
    add(tick, k, 0.10)

# --- whoosh on every cut (camera whip) ---
for c in SHOTS[1:-1]:
    n = int(0.6 * SR); x = bandnoise(n, 300, 6000)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    sweep = np.sin(2 * np.pi * np.cumsum(np.linspace(200, 1200, n)) / SR) * 0.15
    add((x + sweep) * e, c - 0.32, 0.45, pan=0.3)

# --- low hit on each new shot ---
def boom(n_s=1.2, f0=60):
    n = int(n_s * SR); tt = np.arange(n) / SR
    return np.sin(2 * np.pi * (f0 * tt + 20 * (1 - np.exp(-tt * 8)))) * np.exp(-tt * 3.5)
for c in SHOTS[1:-1]:
    add(boom(), c, 0.35)
add(boom(2.0, 45), 0.0, 0.5)

# --- fire: crackle + roar during the fall (shot 4), the wreck (5) and the end (12) ---
def fire(n_s, intensity=1.0):
    n = int(n_s * SR); roar = bandnoise(n, 80, 900) * 0.6
    crack = np.zeros(n); idx = rng.integers(0, n - 400, int(n_s * 40))
    for i in idx: m = 300; crack[i:i + m] += rng.standard_normal(m) * np.exp(-np.arange(m) / 40)
    return (roar + crack * 0.25) * env(n, 0.3, 0.5) * intensity
add(fire(SHOTS[4] - SHOTS[3] + 0.3), SHOTS[3] + 0.2, 0.55)
add(fire(SHOTS[5] - SHOTS[4]), SHOTS[4], 0.3)
add(fire(SHOTS[12] - SHOTS[11]), SHOTS[11], 0.5)
add(boom(2.5, 38), SHOTS[3] + 0.5, 0.6)  # the ignition

# --- storm: rain + thunder (shot 8) ---
rain = bandnoise(int((SHOTS[8] - SHOTS[7]) * SR), 1500, 9000) * env(int((SHOTS[8] - SHOTS[7]) * SR), 0.4, 0.4)
add(rain, SHOTS[7], 0.12)
for k in (0.4, 1.9, 3.6):
    n = int(2.2 * SR); th = bandnoise(n, 30, 500) * np.exp(-np.arange(n) / (0.6 * SR)); th[: int(0.05 * SR)] *= 2.5
    add(th, SHOTS[7] + k, 0.5, pan=-0.2 if k > 1 else 0.2)

# --- static spark zaps (shot 10) ---
for k in np.arange(SHOTS[9] + 1.8, SHOTS[10], 0.25):
    n = int(0.08 * SR); z = np.sign(np.sin(2 * np.pi * 1800 * np.arange(n) / SR)) * np.exp(-np.arange(n) / (0.02 * SR)) * 0.5 + bandnoise(n, 4000, 12000) * 0.5
    add(z, k, 0.22)

# --- stamp thud (shot 7 law + shot 11 folder) ---
def thud():
    n = int(0.35 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * 90 * tt) * np.exp(-tt * 18) + bandnoise(n, 200, 2500) * np.exp(-tt * 30) * 0.5)
add(thud(), SHOTS[6] + 2.4, 0.6); add(thud(), SHOTS[10] + 0.3, 0.7)

# --- final lift + cut ---
n = int((SHOTS[12] - SHOTS[11]) * SR); tt = np.arange(n) / SR
lift = sum(np.sin(2 * np.pi * f * tt) for f in (146.83, 220.0, 293.66)) * np.clip(tt / 1.5, 0, 1) * 0.12
add(lift * env(n, 0.05, 0.4), SHOTS[11])

mix = np.stack([L, R], 1)
mix = np.tanh(mix * 1.4) / np.tanh(1.4)
mix = mix / np.abs(mix).max() * 0.85
out = pathlib.Path(sys.argv[1])
with wave.open(str(out), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out, f'{DUR:.1f}s')
