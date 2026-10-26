"""Muzik latar asli 20 saat, 120 BPM (1 beat = 0.5 s), dijana sepenuhnya dengan numpy.
Babak video bertukar tepat pada beat: 0, 4, 6, 8.5, 11, 13.5, 16 s."""
import numpy as np, wave, sys

SR = 44100
DUR = 20.0
BPM = 120
BEAT = 60 / BPM
N = int(SR * DUR)
out = np.zeros((N, 2))
rng = np.random.default_rng(7)
CUTS = [4, 6, 8.5, 11, 13.5, 16]


def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    out[i:i + len(sig), 0] += sig * (1 - pan) / 2 * 2 ** 0.5
    out[i:i + len(sig), 1] += sig * (1 + pan) / 2 * 2 ** 0.5


def env(n, a, d):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    e[na:] = np.exp(-np.arange(n - na) / (d * SR))
    return e


def hz(m):
    return 440 * 2 ** ((m - 69) / 12)


def kick():
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.16) + \
        rng.standard_normal(n) * np.exp(-t * 300) * 0.3


def clap():
    n = int(0.3 * SR); t = np.arange(n) / SR
    s = rng.standard_normal(n)
    s = np.convolve(s, [1, -0.9], 'same')
    e = sum(np.exp(-np.clip(t - o, 0, None) * 60) * (t >= o) for o in (0, 0.011, 0.022))
    return s * e * 0.35


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    s = np.diff(rng.standard_normal(n + 1))
    return s * env(n, 0.001, 0.06 if open_ else 0.012) * 0.25


def saw(f, n, det=(0, 0.11, -0.11)):
    t = np.arange(n) / SR
    return sum(2 * ((t * f * 2 ** (d / 12)) % 1) - 1 for d in det) / len(det)


def lowpass(x, a):
    y = np.zeros_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y


def lp_fast(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, 'same')


# Am - F - C - G, satu chord satu bar (2 s)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 55, 60, 64], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]

for bar in range(10):
    t0 = bar * 4 * BEAT
    ch = CHORDS[bar % 4]
    # pad
    n = int(4 * BEAT * SR)
    pad = sum(saw(hz(m), n) for m in ch) / len(ch)
    pad = lp_fast(pad, 18) * env(n, 0.25, 3.0)
    add(pad, t0, 0.16 if bar >= 2 else 0.22, 0)
    # arpeggio pluck 16th (masuk bar 1)
    if bar >= 1:
        arp = ch + [ch[0] + 12]
        for s in range(16):
            if bar == 9 and s >= 8:
                break
            m = arp[[0, 1, 2, 3, 2, 1, 3, 2][s % 8]] + 12
            nn = int(0.2 * SR); t = np.arange(nn) / SR
            p = (np.sign(np.sin(2 * np.pi * hz(m) * t)) * 0.5 + np.sin(2 * np.pi * hz(m) * t)) * env(nn, 0.002, 0.07)
            add(lp_fast(p, 4), t0 + s * BEAT / 4, 0.09, 0.35 if s % 2 else -0.35)
    if bar < 2:
        continue
    # drum & bass dari 4 s
    last = bar == 9
    for b in range(4):
        tb = t0 + b * BEAT
        if last and b >= 2:
            break
        add(kick(), tb, 0.9)
        if b in (1, 3):
            add(clap(), tb, 0.8, 0.1)
        add(hat(), tb + BEAT / 2, 0.8, 0.3)
        add(hat(), tb + BEAT / 4, 0.35, -0.3)
        add(hat(), tb + 3 * BEAT / 4, 0.35, -0.3)
        nb = int(BEAT / 2 * SR)
        bs = saw(hz(ROOTS[bar % 4]), nb, (0,)) * 0.6 + np.sin(2 * np.pi * hz(ROOTS[bar % 4]) * np.arange(nb) / SR)
        add(lp_fast(bs, 10) * env(nb, 0.005, 0.18), tb + BEAT / 2, 0.32)

# riser sebelum drop (2-4 s) dan sebelum outro (14.5-16 s)
for (a, b) in [(2.0, 4.0), (14.5, 16.0)]:
    n = int((b - a) * SR); t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    r = np.convolve(noise, [1, -1], 'same') * (t / t[-1]) ** 2
    sweep = np.sin(2 * np.pi * np.cumsum(300 + 1500 * (t / t[-1]) ** 2) / SR) * (t / t[-1]) ** 3 * 0.3
    add((r * 0.12 + sweep * 0.5), a, 0.5)

# whoosh + impact pada setiap pertukaran babak
for c in CUTS:
    n = int(0.5 * SR); t = np.arange(n) / SR
    w = lp_fast(rng.standard_normal(n), 6) * np.sin(np.pi * t / t[-1]) ** 2
    add(w, c - 0.3, 0.35, 0)
    boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 8)) / SR) * env(n, 0.002, 0.35)
    add(boom, c, 0.55 if c in (4, 16) else 0.3)
    if c in (4, 16):
        crash = lp_fast(np.diff(rng.standard_normal(int(1.6 * SR) + 1)), 2) * env(int(1.6 * SR), 0.002, 0.5)
        add(crash, c, 0.18)

# chord akhir panjang 18-20 s
n = int(2.0 * SR)
fin = sum(saw(hz(m), n) for m in [57, 60, 64, 69]) / 4
add(lp_fast(fin, 12) * env(n, 0.01, 0.9), 18.0, 0.25)
add(kick(), 18.0, 1.0)

# master: fade in/out, soft clip, normalise
t = np.arange(N) / SR
out *= np.clip(t / 0.05, 0, 1)[:, None] * np.clip((DUR - t) / 1.2, 0, 1)[:, None]
out = np.tanh(out * 1.3)
out /= np.abs(out).max() / 0.89
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('ok')
