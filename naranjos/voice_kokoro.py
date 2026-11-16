"""Generate the narration with local Kokoro (ONNX) and align words with faster-whisper.

usage: python3 voice_kokoro.py <kokoro_dir> [voice] [speed]
Writes voice.mp3 and words.json (one [start, end] per word of scenes.WORDS).
"""
import sys, os, re, json, subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro
import scenes as SC

HERE = os.path.dirname(os.path.abspath(__file__))
kdir = sys.argv[1]
voice = sys.argv[2] if len(sys.argv) > 2 else 'em_alex'
speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.1

text = ' '.join(SC.WORDS)
# split into sentences, keeping the final fragment
sents = re.findall(r'[^.?!]+[.?!]?', text)
sents = [s.strip() for s in sents if s.strip()]
k = Kokoro(os.path.join(kdir, 'model.onnx'), os.path.join(kdir, 'voices.bin'))
a, sr = k.create(text, voice=voice, speed=speed, lang='es-419')
nz = np.where(np.abs(a) > 0.01)[0]
audio = a[max(0, nz[0] - 2400): nz[-1] + 600]
audio = audio / max(1e-6, np.abs(audio).max()) * 0.89
wav = os.path.join(HERE, 'out', 'voice.wav')
sf.write(wav, audio, sr)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11',
                '-ar', '48000', '-b:a', '192k', os.path.join(HERE, 'voice.mp3')], check=True)
print('duration', len(audio) / sr)

# ---- align with whisper word timestamps
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8')
w16 = wav.replace('.wav', '16.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ar', '16000', '-ac', '1', w16], check=True)
a16, _ = sf.read(w16, dtype='float32')
segs, _ = m.transcribe(a16, language='es', word_timestamps=True, initial_prompt=text)
ww = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
print('whisper words', len(ww), 'script words', len(SC.WORDS))
print(' '.join(w for w, _, _ in ww))


def norm(w):
    w = w.lower()
    for a, b in zip('áéíóúü', 'aeiouu'):
        w = w.replace(a, b)
    return re.sub(r'[^a-zñ0-9]', '', w)


# sequence alignment (DP) between script words and whisper words
A = [norm(w) for w in SC.WORDS]; B = [norm(w) for w, _, _ in ww]
n, mm = len(A), len(B)
D = np.zeros((n + 1, mm + 1)); D[:, 0] = np.arange(n + 1); D[0, :] = np.arange(mm + 1)
for i in range(1, n + 1):
    for j in range(1, mm + 1):
        c = 0 if A[i - 1] == B[j - 1] else 1
        D[i, j] = min(D[i - 1, j - 1] + c, D[i - 1, j] + 1, D[i, j - 1] + 1)
i, j = n, mm; match = {}
while i > 0 and j > 0:
    c = 0 if A[i - 1] == B[j - 1] else 1
    if D[i, j] == D[i - 1, j - 1] + c:
        match[i - 1] = j - 1; i -= 1; j -= 1
    elif D[i, j] == D[i - 1, j] + 1:
        i -= 1
    else:
        j -= 1
times = [None] * n
for i2, j2 in match.items():
    times[i2] = [float(ww[j2][1]), float(ww[j2][2])]
# interpolate missing
known = [i2 for i2 in range(n) if times[i2]]
for i2 in range(n):
    if times[i2] is None:
        prv = max([k2 for k2 in known if k2 < i2], default=None); nxt = min([k2 for k2 in known if k2 > i2], default=None)
        t0 = times[prv][1] if prv is not None else 0.0
        t1 = times[nxt][0] if nxt is not None else len(audio) / sr
        span = (nxt if nxt is not None else n) - (prv if prv is not None else -1)
        f = (i2 - (prv if prv is not None else -1)) / span
        s = t0 + (t1 - t0) * f
        times[i2] = [s, s + (t1 - t0) / span]
print('unmatched', n - len(match))
json.dump(times, open(os.path.join(HERE, 'words.json'), 'w'))
