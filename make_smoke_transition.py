"""Pixel smoke stinger: 1.5 s, fully opaque at the midpoint, transparent everywhere else."""
import subprocess, numpy as np
import os

W, H, S, N, FPS = 480, 270, 4, 45, 30
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smoke-transition.webm")
rs = np.random.RandomState(7)
lat = rs.rand(256, 256)

def noise(x, y):
    xi, yi = np.floor(x).astype(int), np.floor(y).astype(int)
    f, g = x - xi, y - yi
    f, g = f * f * (3 - 2 * f), g * g * (3 - 2 * g)
    a, b = lat[yi % 256, xi % 256], lat[yi % 256, (xi + 1) % 256]
    c, d = lat[(yi + 1) % 256, xi % 256], lat[(yi + 1) % 256, (xi + 1) % 256]
    return (a * (1 - f) + b * f) * (1 - g) + (c * (1 - f) + d * f) * g

def fbm(x, y):
    return noise(x, y) * .6 + noise(x * 2.1, y * 2.1) * .28 + noise(x * 4.3, y * 4.3) * .12

SHADES = np.array([[10, 10, 10], [27, 27, 27], [47, 47, 47], [71, 71, 71], [98, 98, 98], [126, 126, 126]], np.uint8)
Y, X = np.mgrid[0:H:2, 0:W:2].astype(float)
PROMPT = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (3, 5), (2, 6), (1, 7), (0, 8)]

ff = subprocess.Popen(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
                       "-s", f"{W*S}x{H*S}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libvpx-vp9",
                       "-pix_fmt", "yuva420p", "-crf", "30", "-b:v", "0", "-auto-alt-ref", "0", OUT], stdin=subprocess.PIPE)
amp = 70
for i in range(N):
    p = i / (N - 1)
    t = p * 2.6
    lead = -amp - 10 + min(p * 2, 1) * (W + 2 * amp + 20)
    trail = -amp - 10 + max(p * 2 - 1, 0) * (W + 2 * amp + 20)
    n = fbm(X * .022 - t, Y * .03 + t * .3)
    disp = (fbm(X * .01 + 9 + t * .4, Y * .018 - t * .6) - .5) * amp * 2
    edge = X + disp
    mask = (edge < lead) & (edge >= trail) if p < 1 else np.zeros_like(X, bool)
    if p >= .5:
        mask = edge >= trail
    if p <= .5:
        mask = edge < lead
    if i == N // 2:
        mask[:] = True                       # guaranteed full cover on the cut frame
    lv = np.clip(np.floor((n - .3) * 11), 0, 5).astype(int)
    rgb = SHADES[lv]
    a = (mask * 255).astype(np.uint8)
    img = np.dstack([rgb, a])
    img = np.repeat(np.repeat(img, 2, 0), 2, 1)[:H, :W]

    show = 1 - min(abs(p - .5) / .3, 1)      # >_ glows in around the cut
    if show > 0:
        cx, cy = W // 2, H // 2
        yy, xx = np.mgrid[0:H, 0:W]
        for rx, ry, col in ((76, 50, (26, 18, 8)), (62, 40, (43, 26, 8)), (46, 30, (71, 41, 10))):
            ell = ((xx - cx) / (rx * (.5 + show * .5))) ** 2 + ((yy - cy) / (ry * (.5 + show * .5))) ** 2 < 1
            ell &= img[..., 3] > 0
            img[ell, :3] = col
        if show > .25:
            sz, ox, oy = 6, cx - 28, cy - 24
            for a_, b_ in PROMPT:
                img[oy + b_ * sz:oy + (b_ + 1) * sz, ox + a_ * sz:ox + (a_ + 2) * sz] = (255, 154, 26, 255)
            img[oy + 48:oy + 56, ox + 36:ox + 68] = (255, 154, 26, 255)
    big = np.repeat(np.repeat(img, S, 0), S, 1)
    ff.stdin.write(big.tobytes())
ff.stdin.close()
print("ffmpeg exit", ff.wait())
