"""Kokoro (es-419) narration + faster-whisper word alignment -> voice.mp3, words.json"""
import sys, os, re, json, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__))
kdir, voice, speed = sys.argv[1], sys.argv[2], float(sys.argv[3])
paras = [l.strip() for l in open(os.path.join(HERE, 'script.txt')) if l.strip()]
words = ' '.join(paras).split()
k = Kokoro(os.path.join(kdir, 'model.onnx'), os.path.join(kdir, 'voices.bin'))
parts = []; sr = 24000
for p in paras:
    a, sr = k.create(p.replace('…', ',').replace('...', ','), voice=voice, speed=speed, lang='es-419')
    nz = np.where(np.abs(a) > 0.01)[0]
    parts.append(a[max(0, nz[0] - 2400): nz[-1] + 1500])
    parts.append(np.zeros(int(sr * 0.32), np.float32))
audio = np.concatenate(parts[:-1]); audio = audio / np.abs(audio).max() * 0.89
wav = os.path.join(HERE, 'out', 'voice.wav'); sf.write(wav, audio, sr)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11', '-ar', '48000',
                '-b:a', '192k', os.path.join(HERE, 'voice.mp3')], check=True)
print('duration', len(audio) / sr)
from faster_whisper import WhisperModel
m = WhisperModel('small', device='cpu', compute_type='int8')
w16 = wav.replace('.wav', '16.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-ar', '16000', '-ac', '1', w16], check=True)
a16, _ = sf.read(w16, dtype='float32')
segs, _ = m.transcribe(a16, language='es', word_timestamps=True, initial_prompt=' '.join(paras))
ww = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
print(' '.join(w for w, _, _ in ww))
def norm(w):
    w = w.lower()
    for a, b in zip('áéíóúü', 'aeiouu'): w = w.replace(a, b)
    return re.sub(r'[^a-zñ0-9]', '', w)
A = [norm(w) for w in words]; B = [norm(w) for w, _, _ in ww]
n, mm = len(A), len(B)
D = np.zeros((n + 1, mm + 1)); D[:, 0] = np.arange(n + 1); D[0, :] = np.arange(mm + 1)
for i in range(1, n + 1):
    for j in range(1, mm + 1):
        D[i, j] = min(D[i-1, j-1] + (A[i-1] != B[j-1]), D[i-1, j] + 1, D[i, j-1] + 1)
i, j = n, mm; match = {}
while i > 0 and j > 0:
    if D[i, j] == D[i-1, j-1] + (A[i-1] != B[j-1]): match[i-1] = j-1; i -= 1; j -= 1
    elif D[i, j] == D[i-1, j] + 1: i -= 1
    else: j -= 1
times = [None] * n
for a_, b_ in match.items(): times[a_] = [float(ww[b_][1]), float(ww[b_][2])]
for a_ in range(n):
    if times[a_] is None:
        prv = next((times[q][1] for q in range(a_-1, -1, -1) if times[q]), 0.0)
        times[a_] = [prv, prv + 0.2]
print('unmatched', n - len(match), 'words', n)
json.dump({'words': words, 'times': times, 'duration': len(audio) / sr}, open(os.path.join(HERE, 'words.json'), 'w'), ensure_ascii=False)
