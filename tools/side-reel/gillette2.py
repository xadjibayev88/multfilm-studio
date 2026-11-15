"""Gillette 1903-1904, v2 (stronger hook, visual hook; voices/gillette2): story drawing for side_reel.py. Facts: 51 razors + 168 blades in 1903; 90,884 razors + 123,648 blades in 1904."""
import math, random
from contextlib import contextmanager
from PIL import Image, ImageDraw
from side_reel import sky, ease, lerp, mix, pop, font, INK, W, H, Y0

GROUND_DAY, GROUND_NIGHT = (205, 180, 142), (72, 74, 108)
REPLACE = [
    ("bir ming to'qqiz yuz uchinchi yil", "1903-yil"),
    ("bir ming to'qqiz yuz to'rtinchi yilda", "1904-yilda"),
    ("bir yuz yigirma uch mingdan", "123 mingdan"),
    ("bir yuz oltmish sakkizta", "168 ta"),
    ("to'qson mingdan", "90 mingdan"),
    ("ellik bitta", "51 ta"),
]
T = []
STARS = []
YEL, RED, GRN, STEEL = (255, 214, 64), (226, 74, 62), (88, 190, 110), (176, 188, 200)
CROWD = [((196, 84, 70), None), ((70, 112, 176), (60, 50, 44)), ((214, 160, 60), None), ((120, 86, 150), (90, 60, 40)),
         ((60, 140, 130), None), ((190, 110, 150), (50, 50, 60)), ((110, 130, 70), None)]


def setup(G):
    T[:] = [w["t0"] for w in G["words"]]
    rng = random.Random(7)
    STARS[:] = [(rng.uniform(0, W), rng.uniform(20, 760), rng.choice([1.5, 2, 2, 3]), rng.uniform(0, 6)) for _ in range(70)]


def seg(t, a, b): return max(0.0, min(1.0, (t - a) / max(1e-6, b - a)))


def night(t, G):
    return ease(seg(t, T[43] - 0.9, T[43] + 0.4)) * (1 - ease(seg(t, T[65] - 0.1, T[68] - 0.2)))


def camera(t, G):
    keys = [(0, 95, 1.75), (T[11] - 0.25, 80, 1.42), (T[11] + 0.1, 60, 1.1), (T[17], 60, 1.16), (T[17] + 0.2, 95, 1.6), (T[19] - 0.5, 95, 1.7), (T[19] + 0.5, -330, 1.0), (T[25], -300, 1.06), (T[30] - 0.9, -40, 1.2),
            (T[30] + 0.1, 20, 0.86), (T[43] - 1.0, 20, 0.9), (T[43], 70, 1.3), (T[65] - 0.2, 80, 1.42), (T[68], 250, 0.8),
            (T[82] - 0.9, 280, 0.86), (T[82], 40, 1.3), (T[91] - 0.4, 40, 1.4), (T[91] + 0.3, 30, 1.62), (G["dur"], 30, 1.75)]
    for (t0, x0, z0), (t1, x1, z1) in zip(keys, keys[1:]):
        if t <= t1:
            u = seg(t, t0, t1); u = ease(u) if t1 - t0 < 2.5 else u
            return lerp(x0, x1, u), lerp(z0, z1, u)
    return keys[-1][1], keys[-1][2]


@contextmanager
def hud(c, dy=0.0):
    cx, z = c.cx, c.z
    c.cx, c.z = 0.0, 1.0
    Y = c.Y
    c.Y = lambda y: Y(y + dy)
    try: yield
    finally: c.cx, c.z = cx, z; del c.Y


def num(n): return f"{int(n):,}".replace(",", " ")


def big(c, x, y, s, t, t0, size=150, col=YEL, label=None):
    if t < t0: return
    k = pop((t - t0) / 0.38)
    c.text(x, y, s, size * k, fill=col, stroke=9)
    if label: c.text(x, y - size * 0.62, label, 52, fill=(255, 255, 255), stroke=6)


def razor(c, t):
    """handle + swappable blade diagram, HUD coords"""
    a, b = T[30], T[43] - 0.7
    if t < a - 0.4 or t > b + 0.5: return
    dy = (1 - ease(seg(t, a - 0.4, a + 0.15))) * 1100 + ease(seg(t, b, b + 0.5)) * 1100
    with hud(c, dy):
        c.rect(-440, 250, 880, 690, (250, 240, 214), r=44, ol=7)
        hl = 0.5 + 0.5 * math.sin(t * 6)
        on_h = T[33] <= t < T[35]; on_b = T[35] <= t < T[37]
        # handle
        c.rect(-26, 330, 52, 320, mix(STEEL, YEL, 0.55 * hl) if on_h else STEEL, r=20, ol=6)
        for k in range(7): c.line([(-26, 372 + k * 30), (26, 384 + k * 30)], w=3)
        c.rect(-150, 646, 300, 34, (140, 150, 164), r=10, ol=6)
        # old blade: dull → slides out and falls; new blade slides in
        out = ease(seg(t, T[39], T[39] + 0.55)); inn = ease(seg(t, T[41], T[41] + 0.5))
        dull = seg(t, T[37], T[38] + 0.6)
        if out < 1:
            bx, by = out * 330, 680 - (out ** 2) * 300
            col = mix((226, 234, 242), (150, 128, 104), dull)
            if on_b: col = mix(col, YEL, 0.55 * hl)
            c.rect(-196 + bx, by, 392, 16, col, r=4, ol=5)
            if dull > 0.5 and out == 0:
                for k in range(6): c.line([(-170 + k * 66, 680), (-158 + k * 66, 672), (-146 + k * 66, 680)], col=(110, 80, 60), w=3)
        if inn > 0:
            c.rect(-196 - (1 - inn) * 520, 680, 392, 16, (232, 242, 250), r=4, ol=5)
            if inn == 1:
                for k in range(3):
                    r = 20 + 14 * math.sin(t * 5 + k)
                    x, y = (-170, 0, 176)[k], (726, 742, 722)[k] + 34
                    c.line([(x - r, y), (x + r, y)], col=YEL, w=5); c.line([(x, y - r), (x, y + r)], col=YEL, w=5)
        c.rect(-162, 696, 324, 46, (150, 160, 174), r=23, ol=6)
        if t >= T[33]:
            c.line([(40, 470), (150, 470)], w=5); c.text(160, 470, "DASTA", 60, fill=(255, 255, 255), anchor="lm")
            if t >= T[34]: c.text(160, 410, "qoladi", 50, fill=GRN, anchor="lm", stroke=5)
        if t >= T[35]:
            c.text(0, 860, "TIG'", 64, fill=(255, 255, 255))
            if t >= T[36]: c.text(0, 800, "almashadi", 50, fill=RED, stroke=5)


def world(c, t):
    n = c.night
    # far skyline (parallax)
    px = c.cx * 0.55
    rng = random.Random(3)
    for k in range(26):
        x = -1500 + k * 150 + px; h = rng.randint(120, 300); w = rng.randint(90, 140)
        c.rect(x, 0, w, h, mix((158, 178, 196), (120, 140, 168), rng.random()), ol=0)
        if rng.random() < 0.4: c.poly([(x, h), (x + w / 2, h + 60), (x + w, h)], (140, 160, 184), ol=0)
    c.cloud(-520 + px * 1.2 + t * 6, 700, 1.0); c.cloud(260 + px * 1.2 + t * 4, 820, 0.8); c.cloud(900 + px * 1.2 + t * 5, 640, 1.1)
    # factory
    fx = -640
    c.rect(fx + 250, 0, 60, 470, (150, 96, 80), ol=6); c.rect(fx + 242, 470, 76, 26, (120, 74, 62), ol=6)
    for k in range(4):
        u = (t * 0.35 + k * 0.25) % 1
        c.ell(fx + 280 + u * 90, 520 + u * 210, 22 + u * 34, 20 + u * 30, mix((236, 236, 240), (150, 176, 204), u), ol=0)
    c.rect(fx, 0, 400, 300, (204, 112, 88), ol=7)
    c.poly([(fx - 20, 300), (fx + 80, 380), (fx + 80, 300), (fx + 180, 380), (fx + 180, 300), (fx + 280, 380), (fx + 280, 300), (fx + 420, 300)], (132, 84, 74), ol=7)
    lit = mix((170, 206, 232), (255, 220, 120), min(1, n * 1.4))
    for k in range(3): c.rect(fx + 36 + k * 122, 150, 84, 90, lit, r=6, ol=6)
    c.rect(fx + 150, 0, 96, 130, (110, 70, 58), r=6, ol=6)
    c.rect(fx + 40, 252, 320, 62, (252, 240, 210), r=10, ol=6)
    c.text(fx + 200, 284, "JILLETT", 46, fill=(204, 60, 50), stroke=0)
    # lamp post
    c.rect(-150, 0, 14, 330, (60, 62, 76), ol=5); c.ell(-143, 344, 26, 22, mix((240, 240, 230), (255, 226, 130), n), ol=5)
    # stall
    sx = 190
    for dx in (0, 250): c.rect(sx + dx, 0, 12, 250, (120, 82, 60), ol=5)
    for k in range(6): c.rect(sx - 16 + k * 49, 250, 49, 54, (226, 74, 62) if k % 2 else (252, 244, 230), ol=5)
    c.rect(sx - 14, 0, 290, 104, (176, 124, 84), r=6, ol=6); c.rect(sx - 24, 104, 310, 20, (140, 96, 66), r=5, ol=6)
    for k in range(5):
        x = sx + 20 + k * 54
        c.rect(x, 124, 8, 46, STEEL, ol=3); c.rect(x - 14, 168, 36, 12, STEEL, r=4, ol=3)
    # tree
    c.rect(700, 0, 30, 170, (120, 86, 60), ol=6); c.ell(715, 250, 110, 120, (96, 168, 100), ol=7)
    c.rect(-1080, 0, 26, 150, (120, 86, 60), ol=6); c.ell(-1067, 220, 96, 104, (104, 176, 104), ol=7)


def draw(c, G):
    t = c.t
    sky(c, stars=STARS)
    n = c.night
    with hud(c):
        sy = 900 - n * 700
        if n < 0.98:
            c.ell(330, sy, 74, 74, (255, 220, 110), ol=0)
        if n > 0.02:
            my = 200 + n * 700
            c.ell(-320, my, 62, 62, (240, 240, 220), ol=0)
            c.d.ellipse([c.X(-298 - 56), c.Y(my + 20 + 56), c.X(-298 + 56), c.Y(my + 20 - 56)], fill=c.img.getpixel((int(c.X(-298)), int(c.Y(my + 130)))))
    world(c, t)

    # customers (1904)
    t4 = T[68]
    if t > t4 - 0.5:
        for k, (col, hat) in enumerate(CROWD):
            u = seg(t, t4 - 0.3 + k * 0.28, t4 + 1.6 + k * 0.28)
            x = lerp(1250 + k * 60, 520 + k * 98, ease(u))
            walk = (t * 1.9 + k * 0.3) if u < 1 else None
            happy = t > T[69]
            c.person(x, h=190 + (k % 3) * 12, body=col, hat=hat, mood="happy" if happy else "calm", walk=walk, face=-1,
                     arm=(0.5 + 0.5 * math.sin(t * 7 + k)) if happy else 0.0, bob=4 * abs(math.sin(t * 6 + k)) if happy else 0)

    # King Gillette
    if t < T[19] - 0.2: x, walk, face = 110, None, 1
    elif t < T[30] - 0.6:
        u = seg(t, T[19], T[29] + 0.4); x = lerp(-470, -210, ease(u)); walk = t * 1.8 if 0 < u < 1 else None; face = 1
    else:
        u = seg(t, T[30] - 0.6, T[30] + 0.6); x = lerp(-210, 110, ease(u)) if t < T[43] - 1 else 110; walk = t * 2.2 if 0 < u < 1 else None; face = 1
    if t >= T[43] - 1: x = 110
    mood, arm, bob = "calm", 0.0, 0.0
    if t >= T[17] and t < T[19] - 0.2: mood = "wow"
    if T[6] <= t < T[11]: mood = "sad"
    if T[11] <= t < T[17]: mood, arm = "happy", 0.6
    if T[25] <= t < T[30] - 0.6: mood, arm = "happy", 0.5 + 0.4 * math.sin(t * 5)
    if T[30] + 0.6 <= t < T[43] - 1: arm = 0.9
    if T[43] - 0.3 <= t < T[68] - 0.6: mood, bob = "sad", -6
    if T[63] <= t < T[68] - 0.6: mood, arm, bob = "calm", 0.95, 0
    if t >= T[69]: mood, arm, bob = "happy", 0.6 + 0.4 * math.sin(t * 6), 5 * abs(math.sin(t * 5))
    if t >= T[82]: arm, bob = 0.2, 0
    if t >= T[91]: mood, arm = "calm", 0.75

    def hold(hx, hy):
        c.rect(hx - 4, hy, 8, 44, STEEL, ol=3); c.rect(hx - 18, hy + 42, 36, 12, STEEL, r=4, ol=3)
    c.person(x, h=232, body=(46, 112, 86), hat=(52, 46, 60), moustache=True, mood=mood, arm=arm, face=face, walk=walk, bob=bob,
             hold=hold if arm > 0.3 else None)
    if T[43] <= t < T[65]:  # sad sweat drop / zzz of empty street
        u = (t * 0.6) % 1
        c.ell(x + 62, 250 - u * 50, 7, 10, (130, 190, 240), ol=3)
    if t >= T[91]: big(c, x - 130, 300, "?", t, T[91], size=120)

    razor(c, t)
    with hud(c):
        if t < T[11]: big(c, 0, 900, "51", t, 1.0, size=240, col=RED, label="ustara, 1 yilda")
        elif t < T[17]: big(c, 0, 900, "90 000+", t, T[14], size=170, col=GRN, label="ustara")
        elif t < T[19] - 0.3: big(c, 0, 880, "?", t, T[17], size=260)
        if T[19] <= t < T[25] - 0.2: big(c, 0, 900, "1903", t, T[19] + 0.2, size=210, col=(255, 255, 255))
        if T[43] <= t < T[65] - 0.1:
            big(c, -250, 900, "51", t, T[51], size=190, col=RED, label="ustara")
            big(c, 250, 900, "168", t, T[55], size=190, col=RED, label="tig'")
        if T[65] <= t < T[68] - 0.1: big(c, 0, 900, "1 yil", t, T[65], size=180, col=(255, 255, 255))
        if T[68] <= t < T[69] - 0.1: big(c, 0, 900, "1904", t, T[68] + 0.2, size=210, col=(255, 255, 255))
        if T[69] <= t < T[82] - 0.5:
            u = ease(seg(t, T[70], T[72])); v = ease(seg(t, T[74], T[80]))
            big(c, 0, 950, num(51 + (90884 - 51) * u), t, T[69], size=150, col=GRN, label="ustara")
            if t >= T[74]: big(c, 0, 740, num(168 + (123648 - 168) * v), t, T[74], size=150, col=YEL, label="tig'")
        if T[87] <= t < T[91] - 0.3: big(c, 0, 900, "VAQT", t, T[89], size=200)
        for t0, t1, n in ((T[14], T[17] + 0.4, 16), (T[70], T[82] - 0.6, 22)):   # razors raining
            if t0 <= t < t1:
                rng = random.Random(11)
                for k in range(n):
                    x = rng.uniform(-520, 520); sp = rng.uniform(620, 980); ph = rng.uniform(0, 1500)
                    y = 1300 - ((t - t0) * sp + ph) % 1500
                    if y < 60 or (t - t0) * sp + ph < 1500 * 0.2: continue
                    c.rect(x - 4, y, 9, 52, STEEL, ol=3); c.rect(x - 20, y + 50, 40, 13, STEEL, r=4, ol=3)


HITS = []


def shake(t, G):
    if not HITS: HITS[:] = [0.06, 0.52, T[7], T[14], T[17], T[51], T[55], T[69], T[74]]
    dx = dy = 0.0
    for h in HITS:
        u = t - h
        if 0 <= u < 0.45:
            a = 26 * math.exp(-9 * u)
            dx += a * math.sin(u * 95); dy += a * math.cos(u * 80)
    return dx, dy


def cover(img, t, G):
    """visual hook: giant red 51 on a dark card, a blade slashes the screen and the halves fly apart"""
    if t >= 1.05: return img
    card = Image.new("RGB", (W, H), (22, 18, 30))
    d = ImageDraw.Draw(card)
    k = pop(t / 0.3) if t < 0.3 else 1 + 0.03 * math.sin(t * 40)
    for r in range(9):                                   # red burst rays
        a = r * math.tau / 9 + t * 0.8
        d.polygon([(W / 2, 820), (W / 2 + 1500 * math.cos(a), 820 + 1500 * math.sin(a)), (W / 2 + 1500 * math.cos(a + 0.16), 820 + 1500 * math.sin(a + 0.16))], fill=(58, 24, 36))
    d.text((W / 2, 800), "51", font=font(int(720 * k)), fill=RED, anchor="mm", stroke_width=22, stroke_fill=(255, 255, 255))
    d.text((W / 2, 1230), "ta ustara", font=font(120), fill=(255, 255, 255), anchor="mm", stroke_width=10, stroke_fill=(16, 14, 22))
    d.text((W / 2, 1370), "1 yilda. Bor-yo'g'i.", font=font(84), fill=YEL, anchor="mm", stroke_width=9, stroke_fill=(16, 14, 22))
    y0, y1 = H * 0.66, H * 0.30                          # slash line, left to right
    p = ease(seg(t, 0.55, 1.02))
    up = Image.new("L", (W, H), 0); ImageDraw.Draw(up).polygon([(0, 0), (W, 0), (W, y1), (0, y0)], fill=255)
    lo = Image.eval(up, lambda v: 255 - v)
    out = img.copy() if p > 0 else card
    if p > 0:
        ox, oy = int(p * W * 1.15), int(p * 420)
        out.paste(card, (-ox, -oy), up); out.paste(card, (ox, oy), lo)
    s = seg(t, 0.38, 0.62)
    if 0 < s and t < 0.8:                                # the blade flash
        dd = ImageDraw.Draw(out); x = s * W * 1.3
        dd.line([(x - 900, y0 + (y1 - y0) * (x - 900) / W), (x, y0 + (y1 - y0) * x / W)], fill=(255, 255, 255), width=int(34 * (1 - abs(s - 0.5))))
        dd.line([(0, y0), (min(W, x), y0 + (y1 - y0) * min(W, x) / W)], fill=(255, 255, 255), width=6)
    return out


def sfx(G):
    ev = [("thud", 0.05, 0.8), ("whoosh", 0.55, 0.45, 0.8), ("ding", 0.6, 2637, 0.25), ("thud", 0.55, 0.7), ("whoosh", T[11], 0.5, 0.5)]
    for i in (19, 30, 43, 65, 68, 82, 91): ev.append(("whoosh", T[i] - 0.25, 0.6, 0.5))
    ev += [("whoosh", T[39] + 0.25, 0.4, 0.35), ("whoosh", T[41] + 0.2, 0.4, 0.35), ("whoosh", T[11] - 0.3, 0.5, 0.35)]
    for i in (7, 14, 17, 19, 33, 35, 51, 55, 65, 68, 69, 74, 89, 91): ev.append(("pop", T[i] + 0.02))
    for i in (7, 14, 17, 25, 38, 51, 55, 60, 69, 74, 85, 95): ev.append(("thud", T[i]))
    for a, b in ((70, 72), (74, 80)):
        tt = T[a]
        while tt < T[b]: ev.append(("tick", tt)); tt += 0.07
    ev += [("ding", T[72] + 0.1), ("ding", T[80] + 0.3, 1568), ("ding", T[42] + 0.2, 1760, 0.2), ("wind", T[43] - 0.5, T[65] - T[43] + 1.0)]
    return ev
