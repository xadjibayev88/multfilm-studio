"""Side-view 2D explainer reel (flat world, paper ground, karaoke captions with a yellow word, whoosh SFX).
Story-specific drawing lives in a story module (e.g. gillette.py) that exposes SCENES, REPLACE and draw(frame ctx).
Usage: python3 side_reel.py <story module> <voice.mp3> <words.json> <script.txt> <out.mp4>
"""
import importlib, json, math, os, random, subprocess, sys, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H, FPS, SS = 1080, 1920, 30, 2
Y0 = 1130                      # ground line on screen
HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.path.join(HERE, "fonts", "Baloo2[wght].ttf")
INK = (28, 22, 30)


def font(size, weight=800):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_axes([weight])
    except Exception: pass
    return f


def ease(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return a + (b - a) * t
def mix(c1, c2, t): return tuple(int(round(lerp(a, b, t))) for a, b in zip(c1, c2))
def pop(t): t = max(0.0, min(1.0, t)); return 1 + 0.28 * math.sin(t * math.pi) * (1 - t) if t < 1 else 1


# ---------- paper ground texture ----------
def paper(seed=3, size=(1400, 900)):
    rng = np.random.default_rng(seed)
    acc = np.zeros(size[::-1])
    for k, amp in ((6, 1.0), (14, 0.7), (40, 0.45), (120, 0.3)):
        n = rng.random((size[1] // k + 2, size[0] // k + 2))
        im = Image.fromarray((n * 255).astype(np.uint8)).resize(size, Image.BICUBIC)
        acc += np.asarray(im, float) / 255 * amp
    acc = (acc - acc.min()) / (acc.max() - acc.min())
    im = Image.fromarray((acc * 255).astype(np.uint8)).filter(ImageFilter.EMBOSS).filter(ImageFilter.GaussianBlur(0.7))
    return np.asarray(im, float) / 255 - 0.5


PAPER = paper()


def ground(img, col, shift):
    gh = H - Y0
    tw = PAPER.shape[1]
    x0 = int(shift) % (tw - W)
    tex = PAPER[:gh, x0:x0 + W]
    base = np.array(col, float)[None, None, :]
    arr = np.clip(base + tex[:, :, None] * 95, 0, 255).astype(np.uint8)
    img.paste(Image.fromarray(arr, "RGB"), (0, Y0))


# ---------- camera + drawing context (scene layer is drawn at SS x) ----------
class Ctx:
    def __init__(self, t, f, cam, night):
        self.t, self.f, self.cx, self.z, self.night = t, f, cam[0], cam[1], night
        self.img = Image.new("RGB", (W * SS, (Y0 + 40) * SS))
        self.d = ImageDraw.Draw(self.img)

    def X(self, x): return (W / 2 + (x - self.cx) * self.z) * SS
    def Y(self, y): return (Y0 - y * self.z) * SS
    def S(self, v): return v * self.z * SS
    def lw(self, v=5): return max(2, int(round(self.S(v))))
    def tone(self, c, k=0.42): return mix(c, mix(c, (38, 44, 78), 0.75), self.night * k / 0.42 * 0.62)

    def rect(self, x, y, w, h, fill, r=0, ol=5, outline=INK):
        box = [self.X(x), self.Y(y + h), self.X(x + w), self.Y(y)]
        self.d.rounded_rectangle(box, radius=self.S(r), fill=self.tone(fill) if fill else None, outline=outline if ol else None, width=self.lw(ol) if ol else 0)

    def ell(self, x, y, rx, ry, fill, ol=5):
        self.d.ellipse([self.X(x - rx), self.Y(y + ry), self.X(x + rx), self.Y(y - ry)], fill=self.tone(fill) if fill else None, outline=INK if ol else None, width=self.lw(ol) if ol else 0)

    def poly(self, pts, fill, ol=5):
        p = [(self.X(x), self.Y(y)) for x, y in pts]
        self.d.polygon(p, fill=self.tone(fill))
        if ol: self.d.line(p + [p[0]], fill=INK, width=self.lw(ol), joint="curve")

    def line(self, pts, col=INK, w=6):
        self.d.line([(self.X(x), self.Y(y)) for x, y in pts], fill=col, width=self.lw(w), joint="curve")

    def text(self, x, y, s, size, fill=(255, 255, 255), stroke=6, anchor="mm", weight=800):
        f = font(max(8, int(self.S(size))), weight)
        self.d.text((self.X(x), self.Y(y)), s, font=f, fill=fill, anchor=anchor, stroke_width=int(self.S(stroke)), stroke_fill=INK)

    # flat cartoon person, feet at (x, 0)
    def person(self, x, h=210, body=(46, 110, 84), skin=(250, 222, 196), mood="calm", walk=None, hat=None, moustache=False, arm=0.0, face=1, y=0.0, bob=0.0, hold=None):
        hr = h * 0.2
        leg = h * 0.34
        by = y + leg + bob
        ph = 0 if walk is None else walk
        sw = math.sin(ph * math.tau) * h * 0.09 if walk is not None else 0
        for s in (-1, 1):
            self.line([(x + s * h * 0.045, by + 4), (x + s * h * 0.045 + s * sw, y)], w=h * 0.03)
            self.line([(x + s * h * 0.045 + s * sw - 2, y), (x + s * h * 0.045 + s * sw + face * h * 0.06, y)], w=h * 0.03)
        bh = h * 0.3
        self.ell(x, by + bh / 2, h * 0.115, bh / 2 + 4, body, ol=h * 0.026)
        for k in range(3):
            self.ell(x + face * 3, by + bh * (0.25 + 0.22 * k), 2.6, 2.6, mix(body, (0, 0, 0), 0.45), ol=0)
        sh = by + bh * 0.82
        self.line([(x - face * h * 0.1, sh), (x - face * h * 0.15, by + bh * 0.25)], w=h * 0.028)
        ax, ay = x + face * h * 0.1, sh
        hx, hy = ax + face * h * (0.07 + 0.08 * arm), ay - h * 0.2 + h * 0.42 * arm
        self.line([(ax, ay), (hx, hy)], w=h * 0.028)
        self.ell(hx, hy, h * 0.022, h * 0.022, INK, ol=0)
        if hold: hold(hx, hy)
        cy = by + bh + hr * 0.82
        self.ell(x, cy, hr * 1.02, hr, skin, ol=h * 0.03)
        ex = hr * 0.38
        for s in (-1, 1):
            cxp = x + s * ex + face * hr * 0.12
            if mood == "sad":
                self.line([(cxp - hr * 0.16, cy + hr * 0.02), (cxp, cy + hr * 0.12), (cxp + hr * 0.16, cy + hr * 0.02)], w=h * 0.016)
            elif mood == "wow":
                self.ell(cxp, cy + hr * 0.1, hr * 0.09, hr * 0.12, INK, ol=0)
            else:
                self.line([(cxp - hr * 0.16, cy + hr * 0.08), (cxp, cy + hr * 0.18), (cxp + hr * 0.16, cy + hr * 0.08)], w=h * 0.016)
        mx = x + face * hr * 0.12
        if moustache:
            self.line([(mx - hr * 0.3, cy - hr * 0.3), (mx, cy - hr * 0.2), (mx + hr * 0.3, cy - hr * 0.3)], col=(70, 44, 30), w=h * 0.03)
        if mood == "happy":
            self.d.pieslice([self.X(mx - hr * 0.26), self.Y(cy - hr * 0.2), self.X(mx + hr * 0.26), self.Y(cy - hr * 0.72)], 0, 180, fill=(120, 30, 40), outline=INK, width=self.lw(h * 0.012))
        elif mood == "sad":
            self.line([(mx - hr * 0.2, cy - hr * 0.55), (mx, cy - hr * 0.44), (mx + hr * 0.2, cy - hr * 0.55)], w=h * 0.016)
        elif mood == "wow":
            self.ell(mx, cy - hr * 0.5, hr * 0.12, hr * 0.15, (120, 30, 40), ol=h * 0.012)
        else:
            self.line([(mx - hr * 0.18, cy - hr * 0.46), (mx, cy - hr * 0.54), (mx + hr * 0.18, cy - hr * 0.46)], w=h * 0.016)
        if hat:
            self.rect(x - hr * 1.15, cy + hr * 0.62, hr * 2.3, hr * 0.22, hat, r=4, ol=h * 0.024)
            self.rect(x - hr * 0.68, cy + hr * 0.8, hr * 1.36, hr * 0.8, hat, r=6, ol=h * 0.024)
            self.rect(x - hr * 0.68, cy + hr * 0.84, hr * 1.36, hr * 0.2, mix(hat, (255, 255, 255), 0.35), ol=0)

    def cloud(self, x, y, s=1.0):
        c = mix((255, 255, 255), (92, 100, 132), self.night * 0.9)
        for dx, dy, r in ((-60, 0, 44), (0, 22, 62), (64, 0, 48), (118, -6, 34), (-110, -8, 30)):
            self.d.ellipse([self.X(x + dx * s - r * s), self.Y(y + dy * s + r * s), self.X(x + dx * s + r * s), self.Y(y + dy * s - r * s)], fill=c)
        self.d.rectangle([self.X(x - 140 * s), self.Y(y - 4 * s), self.X(x + 152 * s), self.Y(y - 40 * s)], fill=c)


def sky(ctx, day=((126, 164, 198), (214, 228, 238)), night=((14, 18, 40), (44, 52, 86)), stars=None):
    n = ctx.night
    top, bot = mix(day[0], night[0], n), mix(day[1], night[1], n)
    hh = ctx.img.size[1]
    grad = np.linspace(0, 1, hh)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - grad) + np.array(bot)[None, None, :] * grad).astype(np.uint8)
    ctx.img.paste(Image.fromarray(np.repeat(arr, 4, axis=1), "RGB").resize(ctx.img.size))
    if n > 0.15 and stars is not None:
        a = int(255 * min(1, (n - 0.15) / 0.5))
        for sx, sy, r, ph in stars:
            tw = 0.6 + 0.4 * math.sin(ctx.t * 2.2 + ph)
            c = int(a * tw)
            ctx.d.ellipse([sx * SS - r * SS, sy * SS - r * SS, sx * SS + r * SS, sy * SS + r * SS], fill=mix(top, (255, 255, 255), c / 255))


# ---------- captions (karaoke, yellow current word) ----------
def tokens(words, script, replace):
    raw = script.split()
    toks = [{"w": (raw[i] if len(raw) == len(words) else w["w"]).replace("\u02bb", "'"), "t0": w["t0"], "t1": w["t1"]} for i, w in enumerate(words)]
    norm = lambda s: s.lower().strip(".,:;!?…\"'")
    out, i = [], 0
    while i < len(toks):
        hit = None
        for pat, disp in replace:
            p = pat.split()
            if [norm(t["w"]) for t in toks[i:i + len(p)]] == p:
                tail = toks[i + len(p) - 1]["w"]
                punct = tail[len(tail.rstrip(".,:;!?…")):]
                hit = ({"w": disp + punct, "t0": toks[i]["t0"], "t1": toks[i + len(p) - 1]["t1"]}, len(p)); break
        if hit: out.append(hit[0]); i += hit[1]
        else: out.append(toks[i]); i += 1
    return out


def chunks(toks, max_chars=24, max_words=4, gap=0.42):
    groups, cur = [], []
    for k, t in enumerate(toks):
        cur.append(t)
        end = t["w"][-1] in ".?!…:" or (k + 1 < len(toks) and toks[k + 1]["t0"] - t["t1"] > gap)
        length = sum(len(x["w"]) + 1 for x in cur)
        last_short = k + 2 >= len(toks) or toks[k + 1]["w"][-1] in ".?!…"
        if end or ((length >= max_chars or len(cur) >= max_words) and not (last_short and len(cur) < 6)) or (t["w"][-1] == "," and length > 14):
            groups.append(cur); cur = []
    if cur: groups.append(cur)
    return groups


def caption(img, group, t, key=None):
    if not group: return
    f = font(86, 800)
    d = ImageDraw.Draw(img)
    words = [g["w"] for g in group]
    lines, cur = [[]], 0
    total = sum(d.textlength(w + " ", font=f) for w in words)
    half = total / 2 if total > 900 else 1e9
    for i, w in enumerate(words):
        wl = d.textlength(w + " ", font=f)
        if cur + wl / 2 > half and lines[-1]: lines.append([]); cur = 0; half = 1e9
        lines[-1].append(i); cur += wl
    active = max((i for i, g in enumerate(group) if t >= g["t0"] - 0.03), default=0)
    y = 1330 - (len(lines) - 1) * 50
    for ln in lines:
        lw = sum(d.textlength(words[i] + " ", font=f) for i in ln) - d.textlength(" ", font=f)
        x = (W - lw) / 2
        for i in ln:
            col = (255, 214, 64) if i == active else (255, 255, 255)
            d.text((x, y), words[i], font=f, fill=col, stroke_width=10, stroke_fill=(16, 14, 22))
            x += d.textlength(words[i] + " ", font=f)
        y += 100


# ---------- audio: whooshes, pops, dings, soft bed ----------
SR = 48000


def sfx_track(dur, events, bed=True):
    n = int(dur * SR); out = np.zeros(n); rng = np.random.default_rng(5)

    def add(t0, x):
        i = int(t0 * SR)
        if i < 0: x = x[-i:]; i = 0
        m = min(len(x), n - i)
        if m > 0: out[i:i + m] += x[:m]

    def whoosh(t0, d=0.55, g=0.5):
        m = int(d * SR); tt = np.arange(m) / SR
        noise = rng.standard_normal(m)
        env = np.sin(np.pi * tt / d) ** 2.2
        # swept band-pass via two moving one-pole filters
        y = np.zeros(m); lp = 0.0; lp2 = 0.0
        fc = 300 + 3800 * np.sin(np.pi * tt / d) ** 1.5
        a = 1 - np.exp(-2 * np.pi * fc / SR); a2 = 1 - np.exp(-2 * np.pi * (fc * 0.35) / SR)
        for k in range(m):
            lp += a[k] * (noise[k] - lp); lp2 += a2[k] * (noise[k] - lp2); y[k] = lp - lp2
        add(t0 - d / 2, y * env * g * 2.2)

    def popsnd(t0, f=520, g=0.4):
        m = int(0.16 * SR); tt = np.arange(m) / SR
        add(t0, g * np.exp(-tt * 28) * np.sin(2 * np.pi * (f + 500 * np.exp(-tt * 40)) * tt))

    def ding(t0, f=1320, g=0.3):
        m = int(1.1 * SR); tt = np.arange(m) / SR
        add(t0, g * np.exp(-tt * 4.5) * (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.5 * tt) * np.exp(-tt * 6)))

    def thud(t0, g=0.55):
        m = int(0.3 * SR); tt = np.arange(m) / SR
        add(t0, g * np.exp(-tt * 20) * np.sin(2 * np.pi * (95 - 50 * tt) * tt))

    def tick(t0, g=0.18):
        m = int(0.04 * SR); tt = np.arange(m) / SR
        add(t0, g * np.exp(-tt * 120) * np.sin(2 * np.pi * 1900 * tt))

    def wind(t0, d, g=0.1):
        m = int(d * SR); tt = np.arange(m) / SR
        x = rng.standard_normal(m); y = np.zeros(m); lp = 0.0
        fc = 320 + 180 * np.sin(2 * np.pi * 0.18 * tt + 1)
        a = 1 - np.exp(-2 * np.pi * fc / SR)
        for k in range(m):
            lp += a[k] * (x[k] - lp); y[k] = lp
        env = np.minimum(1, tt / 1.2) * np.minimum(1, (d - tt) / 1.2) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.11 * tt))
        add(t0, y * env * g * 6)

    fn = {"whoosh": whoosh, "pop": popsnd, "ding": ding, "thud": thud, "tick": tick, "wind": wind}
    for ev in events: fn[ev[0]](*ev[1:])
    if bed:  # very soft marimba-like bed, 96 bpm
        q = 60 / 96; prog = [(45, 57, 60, 64), (41, 57, 60, 65), (48, 60, 64, 67), (43, 59, 62, 67)]
        bar = 0
        while bar * 4 * q < dur:
            ch = prog[bar % 4]
            for b in range(8):
                t0 = (bar * 4 + b * 0.5) * q; m = ch[0] if b % 4 == 0 else ch[1 + (b * 2) % 3]
                f = 440 * 2 ** ((m - 69) / 12); k = int(0.5 * SR); tt = np.arange(k) / SR
                add(t0, (0.07 if b % 4 else 0.12) * np.exp(-tt * 8) * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)))
            bar += 1
    tt = np.arange(n) / SR
    out *= np.minimum(1, tt / 0.3) * np.minimum(1, (dur - tt) / 1.0)
    return np.clip(out, -1, 1)


def write_wav(path, x):
    pcm = (np.stack([x, x], 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


# ---------- render ----------
G = {}


def frame(f):
    st = G["story"]; t = f / FPS
    cam, night, gcol = st.camera(t, G), st.night(t, G), None
    ctx = Ctx(t, f, cam, night)
    st.draw(ctx, G)
    img = Image.new("RGB", (W, H))
    img.paste(ctx.img.resize((W, Y0 + 40), Image.LANCZOS), (0, 0))
    ground(img, mix(st.GROUND_DAY, st.GROUND_NIGHT, night), cam[0] * cam[1])
    d = ImageDraw.Draw(img)
    d.line([(0, Y0), (W, Y0)], fill=INK, width=5)
    if hasattr(st, "overlay"): st.overlay(img, t, G)
    grp = next((g for g in G["groups"] if g[0]["t0"] - 0.08 <= t < g[-1]["t1"] + 0.25), None)
    caption(img, grp, t)
    if hasattr(st, "shake"):
        dx, dy = st.shake(t, G)
        if dx or dy: img = ImageChops.offset(img, int(dx), int(dy))
    if hasattr(st, "cover"): img = st.cover(img, t, G) or img
    return f, img.tobytes()


def main():
    mod, voice, wjson, script, out = sys.argv[1:6]
    sys.path.insert(0, HERE)
    st = importlib.import_module(mod)
    words = json.load(open(wjson, encoding="utf-8"))
    toks = tokens(words, open(script, encoding="utf-8").read(), st.REPLACE)
    dur = words[-1]["t1"] + 1.4
    G.update(story=st, words=words, toks=toks, groups=chunks(toks), dur=dur)
    st.setup(G)
    total = int(dur * FPS)
    only = os.environ.get("FRAMES")
    if only:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        for f in [int(x) for x in only.split(",")]:
            Image.frombytes("RGB", (W, H), frame(f)[1]).save(f"{out}_{f:05d}.jpg", quality=88)
        return
    tmp = out + ".video.mp4"
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    with Pool(int(os.environ.get("PROCS", "4"))) as pool:
        for f, data in pool.imap(frame, range(total), chunksize=4):
            ff.stdin.write(data)
    ff.stdin.close(); ff.wait()
    sfx = out + ".sfx.wav"
    write_wav(sfx, sfx_track(dur, st.sfx(G)))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", voice, "-i", sfx, "-filter_complex",
                    "[1:a]aresample=48000,asplit[va][vb];[2:a]volume=0.9[m];[m][va]sidechaincompress=threshold=0.04:ratio=5:attack=15:release=260[md];"
                    "[vb][md]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
    os.remove(tmp)
    print("done", out, round(dur, 2), "s")


if __name__ == "__main__":
    main()
