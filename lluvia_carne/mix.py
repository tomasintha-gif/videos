"""mix.py voice music sfx -> out/mix.wav. Music at 50% of voice gated RMS (-6 dB); SFX at <=50% with peaks <= 0.7x voice peak."""
import sys, os, subprocess
import numpy as np
import soundfile as sf

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    tmp = os.path.join(HERE, 'out', '_tmp_' + os.path.basename(p) + '.wav')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-ac', '1', '-ar', str(SR), tmp], check=True)
    x, _ = sf.read(tmp, dtype='float64'); os.remove(tmp); return x


def gated_rms(x, win=0.4):
    n = int(win * SR); k = len(x) // n
    if k == 0: return np.sqrt(np.mean(x ** 2))
    blocks = np.sqrt(np.mean(x[:k * n].reshape(k, n) ** 2, axis=1))
    thr = max(blocks.max() * 10 ** (-40 / 20), 1e-6)
    act = blocks[blocks > thr]
    act = act[act > np.sqrt(np.mean(act ** 2)) * 10 ** (-10 / 20)]  # relative gate
    return np.sqrt(np.mean(act ** 2))


v, m, s = (load(p) for p in sys.argv[1:4])
L = len(v); m = np.pad(m, (0, max(0, L - len(m))))[:L]; s = np.pad(s, (0, max(0, L - len(s))))[:L]
rv = gated_rms(v)
m *= (0.5 * rv) / gated_rms(m)
s *= (0.5 * rv) / gated_rms(s)
cap = 0.7 * np.abs(v).max()
if np.abs(s).max() > cap: s *= cap / np.abs(s).max()
db = lambda a, b: 20 * np.log10(a / b)
print(f'music vs voice: {db(gated_rms(m), rv):+.1f} dB   sfx vs voice: {db(gated_rms(s), rv):+.1f} dB   '
      f'sfx peak / voice peak: {np.abs(s).max() / np.abs(v).max():.2f}')
mix = v + m + s
sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix.astype(np.float32), SR, subtype='FLOAT')
