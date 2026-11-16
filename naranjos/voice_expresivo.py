"""Expressive narration with local Kokoro: per-phrase speed + dramatic pauses, then Whisper word alignment.

usage: python3 voice_expresivo.py <kokoro_dir> [voice]
Writes voice.mp3 and words.json (one [start, end] per word of scenes.WORDS).
"""
import sys, os, re, json, subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
import scenes as SC

HERE = os.path.dirname(os.path.abspath(__file__))
kdir = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else 'em_santa'

# (text, speed, pause after in seconds). Hook and twist slower, explanation faster, final line cut dry for the loop.
SEGS = [
    ("Regó sus naranjos en plena helada.", 0.95, 0.50),
    ("Verás, un comprador iba a elegir una sola finca para todo el invierno.", 1.10, 0.25),
    ("Y esa noche, el pronóstico marcaba cinco bajo cero.", 1.00, 0.40),
    ("El vecino prendió estufas entre las filas y tapó sus árboles con mantas.", 1.12, 0.22),
    ("Él abrió los aspersores... y los dejó toda la noche.", 1.00, 0.40),
    ("¿Vas a vender paletas heladas?, se rió el vecino.", 1.15, 0.22),
    ("Mañana te compro el campo por dos pesos.", 1.08, 0.45),
    ("Al amanecer, su campo era una cueva de hielo.", 1.00, 0.28),
    ("Las ramas crujían, una se partió, y las naranjas colgaban atrapadas en vidrio.", 1.08, 0.32),
    ("El comprador ni lo miró.", 0.95, 0.40),
    ("Fue directo a lo del vecino y cortó una naranja.", 1.10, 0.20),
    ("Cristales de hielo por dentro.", 1.00, 0.30),
    ("Luego otra.", 1.05, 0.20),
    ("Luego todas, crujiendo como granizado.", 1.10, 0.38),
    ("Volvió, rompió el hielo de una de las suyas, y apoyó el cuchillo.", 1.00, 0.55),
    ("Verás, cuando el agua se congela, suelta calor.", 1.05, 0.25),
    ("Mientras siga cayendo agua y congelándose, la fruta queda trabada en cero grados,", 1.12, 0.10),
    ("como una olla que no pasa de cien, por más fuego que le pongas.", 1.12, 0.32),
    ("Y una naranja recién se congela por debajo de los dos bajo cero.", 1.08, 0.50),
    ("El cuchillo salió chorreando jugo.", 1.00, 0.40),
    ("El vecino se quedó con sus mantas,", 1.05, 0.12),
    ("y el comprador firmó todo el invierno con el único loco que", 1.05, 0.0),
]

k = Kokoro(os.path.join(kdir, 'model.onnx'), os.path.join(kdir, 'voices.bin'))
parts = []; sr = 24000
for i, (txt, spd, gap) in enumerate(SEGS):
    a, sr = k.create(txt, voice=voice, speed=spd, lang='es-419')
    nz = np.where(np.abs(a) > 0.01)[0]
    tail = 300 if i == len(SEGS) - 1 else 1500   # dry cut on the last word
    a = a[max(0, nz[0] - 2400): nz[-1] + tail]
    parts += [a, np.zeros(int(sr * gap), np.float32)]
audio = np.concatenate(parts)
audio = audio / np.abs(audio).max() * 0.89
wav = os.path.join(HERE, 'out', 'voice.wav')
os.makedirs(os.path.dirname(wav), exist_ok=True)
sf.write(wav, audio, sr)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11',
                '-ar', '48000', '-b:a', '192k', os.path.join(HERE, 'voice.mp3')], check=True)
print('duration', len(audio) / sr)

# ---- align script words with Whisper timestamps
from faster_whisper import WhisperModel
text = ' '.join(SC.WORDS)
m = WhisperModel('small', device='cpu', compute_type='int8')
w16 = wav.replace('.wav', '16.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ar', '16000', '-ac', '1', w16], check=True)
a16, _ = sf.read(w16, dtype='float32')
segs, _ = m.transcribe(a16, language='es', word_timestamps=True, initial_prompt=text)
ww = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
print(' '.join(w for w, _, _ in ww))


def norm(w):
    w = w.lower()
    for x, y in zip('áéíóúü', 'aeiouu'):
        w = w.replace(x, y)
    return re.sub(r'[^a-zñ0-9]', '', w)


A_ = [norm(w) for w in SC.WORDS]; B_ = [norm(w) for w, _, _ in ww]
n, mm = len(A_), len(B_)
D = np.zeros((n + 1, mm + 1)); D[:, 0] = np.arange(n + 1); D[0, :] = np.arange(mm + 1)
for i in range(1, n + 1):
    for j in range(1, mm + 1):
        D[i, j] = min(D[i - 1, j - 1] + (A_[i - 1] != B_[j - 1]), D[i - 1, j] + 1, D[i, j - 1] + 1)
i, j = n, mm; match = {}
while i > 0 and j > 0:
    if D[i, j] == D[i - 1, j - 1] + (A_[i - 1] != B_[j - 1]):
        match[i - 1] = j - 1; i -= 1; j -= 1
    elif D[i, j] == D[i - 1, j] + 1:
        i -= 1
    else:
        j -= 1
times = [None] * n
for a_, b_ in match.items():
    times[a_] = [float(ww[b_][1]), float(ww[b_][2])]
known = [q for q in range(n) if times[q]]
for q in range(n):
    if times[q] is None:
        prv = max([x for x in known if x < q], default=None); nxt = min([x for x in known if x > q], default=None)
        t0 = times[prv][1] if prv is not None else 0.0
        t1 = times[nxt][0] if nxt is not None else len(audio) / sr
        times[q] = [t0, max(t0 + 0.05, min(t1, t0 + 0.3))]
print('unmatched', n - len(match), 'of', n)
json.dump(times, open(os.path.join(HERE, 'words.json'), 'w'))
