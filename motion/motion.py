"""Моушн-ролики Ummati (9:16): звёздное небо, свечение, кольца, геометрия, плавные появления текста.
Кадры рисуются кодом (PIL + numpy), ничего не генерируется нейросетью.
Тексты аятов — только дословно (арабский quran-uthmani, перевод Э. Кулиева); от себя — лишь короткие связки."""
import math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.environ.get("FONTS", os.path.join(HERE, "..", "fonts"))
GOLD, CREAM, MUTED, EMER = (233, 190, 140), (246, 240, 230), (196, 206, 198), (60, 160, 120)
THEME = None          # задаётся themes.pick(): свой фон/палитра/орнамент на каждый ролик

def font(name, size):
    return ImageFont.truetype(os.path.join(FD, name), size)

AR = lambda s: font("AmiriQuran.woff", s)
SERIF = lambda s: font("CormorantGaramond_500Medium.ttf", s)
SANS = lambda s: font("Montserrat_400Regular.ttf", s)
SANS_B = lambda s: font("Montserrat_600SemiBold.ttf", s)

def ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)

# ---------- фон ----------
def make_background():
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([4, 10, 9]), np.array([9, 26, 21])
    g = top + (bot - top) * y[..., None]
    g = np.repeat(g, W, axis=1)
    xx, yy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    vig = 1 - 0.55 * np.clip(xx ** 2 * 0.8 + yy ** 2 * 0.6, 0, 1)
    return (g * vig[..., None]).astype(np.uint8)

class Stars:
    def __init__(self, n=260, seed=7):
        r = random.Random(seed)
        self.s = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 2.2), r.uniform(0, 6.28), r.uniform(0.4, 1.4)) for _ in range(n)]
    def draw(self, img, t):
        d = ImageDraw.Draw(img)
        for x, y, size, ph, sp in self.s:
            yy = (y - t * 6 * sp) % H
            a = int(110 + 120 * (0.5 + 0.5 * math.sin(ph + t * sp * 1.7)))
            d.ellipse((x - size, yy - size, x + size, yy + size), fill=(230, 235, 255, a))

def glow_sprite(radius, color, power=2.2):
    s = radius * 2
    yy, xx = np.mgrid[0:s, 0:s]
    r = np.sqrt((xx - radius) ** 2 + (yy - radius) ** 2) / radius
    a = np.clip(1 - r, 0, 1) ** power
    arr = np.zeros((s, s, 4), np.uint8)
    arr[..., :3] = color
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")

def paste_alpha(base, sprite, center, alpha=1.0, scale=1.0):
    if alpha <= 0.01:
        return
    sp = sprite if scale == 1 else sprite.resize((max(1, int(sprite.width * scale)), max(1, int(sprite.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        r, g, b, a = sp.split()
        sp = Image.merge("RGBA", (r, g, b, a.point(lambda v: int(v * alpha))))
    base.alpha_composite(sp, (int(center[0] - sp.width / 2), int(center[1] - sp.height / 2)))

# ---------- текст ----------
def wrap(text, f, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def text_block(text, f, color, maxw=900, lh=1.25, glow=0, rtl=False, spacing=0):
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    kw = {"direction": "rtl", "language": "ar"} if rtl else {}
    lines = wrap(text, f, maxw, tmp) if not rtl else wrap_rtl(text, f, maxw, tmp)
    size = f.size
    step = int(size * lh * (1.35 if rtl else 1.0))
    img = Image.new("RGBA", (W, step * len(lines) + size * 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = int(size * 1.5)                                   # базовая линия первой строки
    for ln in lines:
        if spacing:
            tw = d.textlength(ln, font=f) + spacing * (len(ln) - 1); x = (W - tw) / 2
            for ch in ln:
                d.text((x, y), ch, font=f, fill=color, anchor="ls"); x += d.textlength(ch, font=f) + spacing
        else:
            d.text((W / 2, y), ln, font=f, fill=color, anchor="ms", **kw)
        y += step
    bb = img.getbbox() or (0, 0, W, 10)
    img = img.crop((0, max(0, bb[1] - 24), W, min(img.height, bb[3] + 24)))
    if glow:
        g = img.filter(ImageFilter.GaussianBlur(glow))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(img)
        return out
    return img

def wrap_rtl(text, f, maxw, d):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f, direction="rtl", language="ar") <= maxw:
            cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def fade(img, a):
    if a >= 0.999: return img
    r, g, b, al = img.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

class Item:
    """Слой с появлением/исчезновением: t0..t1, плавный подъём на rise пикселей."""
    def __init__(self, img, y, t0, t1, fin=0.8, fout=0.6, rise=30, x=None):
        self.img, self.y, self.t0, self.t1, self.fin, self.fout, self.rise, self.x = img, y, t0, t1, fin, fout, rise, x
    def draw(self, base, t, dim=1.0):
        if t < self.t0 or t > self.t1: return
        a = min(ease((t - self.t0) / self.fin), ease((self.t1 - t) / self.fout)) * dim
        if a <= 0.01: return
        dy = (1 - ease((t - self.t0) / self.fin)) * self.rise
        x = (W - self.img.width) // 2 if self.x is None else int(self.x - self.img.width / 2)
        base.alpha_composite(fade(self.img, a), (x, int(self.y + dy - self.img.height / 2)))

# ---------- геометрия ----------
def draw_rings(base, c, t, alpha, r0=170, n=3, color=None):
    if alpha <= 0.01: return
    color = color or GOLD
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i in range(n):
        r = r0 + i * 46
        a0 = (t * (14 + i * 7) * (1 if i % 2 else -1)) % 360
        span = 230 - i * 40
        d.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), a0, a0 + span, fill=(*color, int(150 * alpha)), width=2)
    base.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3)))
    base.alpha_composite(lay)

def star_points(c, r, k=8, rot=-90):
    return [(c[0] + r * math.cos(math.radians(rot + i * 360 / k)), c[1] + r * math.sin(math.radians(rot + i * 360 / k))) for i in range(k)]

def render(scene, out, dur, audio=None):
    if THEME:
        bg, stars = THEME["bg"], THEME["back"]
    else:
        bg = Image.fromarray(make_background(), "RGB").convert("RGBA")
        stars = Stars()
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", *(["-i", audio] if audio else []),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                            *(["-c:a", "aac", "-b:a", "160k", "-shortest"] if audio else []), "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for i in range(n):
        t = i / FPS
        img = bg.copy()
        stars.draw(img, t)
        scene(img, t)
        a = min(1, ease(t / 0.8), ease((dur - t) / 1.0))
        frame = img.convert("RGB")
        if a < 1:
            frame = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), frame, a)
        enc.stdin.write(frame.tobytes())
    enc.stdin.close(); enc.wait()

# ---------- v2: частицы, ударные кольца, проявление по словам ----------
class Particles:
    """Частицы: burst — разлёт из точки, sink — медленное «осыпание» вниз, orbit — кружение вокруг центра."""
    def __init__(self, n, seed, kind, center, t0, t1, color=None, spread=420):
        r = random.Random(seed)
        self.p = [(r.uniform(0, 6.283), r.uniform(0.3, 1.0), r.uniform(1.0, 3.2), r.uniform(-60, 60)) for _ in range(n)]
        self.kind, self.c, self.t0, self.t1, self.col, self.spread = kind, center, t0, t1, color or GOLD, spread
    def draw(self, img, t):
        if t < self.t0 or t > self.t1: return
        u = (t - self.t0) / (self.t1 - self.t0)
        a_all = min(ease(u / 0.15), ease((1 - u) / 0.25))
        d = ImageDraw.Draw(img)
        for ang, sp, sz, jit in self.p:
            if self.kind == "burst":
                rr = self.spread * sp * ease(min(1, u * 1.6)); x = self.c[0] + rr * math.cos(ang); y = self.c[1] + rr * math.sin(ang)
            elif self.kind == "converge":
                rr = self.spread * sp * (1 - ease(u)); x = self.c[0] + rr * math.cos(ang); y = self.c[1] + rr * math.sin(ang)
            elif self.kind == "sink":
                x = self.c[0] + math.cos(ang) * self.spread * sp; y = self.c[1] + math.sin(ang) * 120 * sp + u * 700 * sp
            else:  # orbit
                rr = self.spread * (0.55 + 0.45 * sp); a2 = ang + u * 2.2 * (0.5 + sp)
                x = self.c[0] + rr * math.cos(a2); y = self.c[1] + rr * 0.55 * math.sin(a2) + jit * 0.3
            al = int(230 * a_all * (0.5 + 0.5 * sp))
            d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=(*self.col, al))

def shock(img, c, t, t0, color=None, r1=330, dur=1.2, width=3):
    color = color or GOLD
    u = (t - t0) / dur
    if u < 0 or u > 1: return
    r = 40 + (r1 - 40) * ease(u); a = int(220 * (1 - u))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=(*color, a), width=width)
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2))); img.alpha_composite(lay)

class Words:
    """Строки, проявляющиеся по словам за время [t0, t0+span] (под темп чтения), затем держатся до t1."""
    def __init__(self, text, f, color, y, t0, span, t1, maxw=900, rtl=False, lh=1.3, glow=0):
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        kw = {"direction": "rtl", "language": "ar"} if rtl else {}
        lines = (wrap_rtl if rtl else wrap)(text, f, maxw, tmp)
        self.words = []                       # (img, x, y) по порядку чтения
        step = int(f.size * lh * (1.35 if rtl else 1.0))
        total_h = step * len(lines)
        y0 = y - total_h / 2 + f.size
        for li, ln in enumerate(lines):
            ws = ln.split()
            full = tmp.textlength(ln, font=f, **kw); sp = tmp.textlength(" ", font=f)
            x = (W + full) / 2 if rtl else (W - full) / 2
            for w in ws:
                wl = tmp.textlength(w, font=f, **kw)
                im = Image.new("RGBA", (int(wl) + 40, int(f.size * 2.4)), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((20, int(f.size * 1.6)), w, font=f, fill=color, anchor="ls", **kw)
                if glow:
                    g = im.filter(ImageFilter.GaussianBlur(glow)); o = Image.new("RGBA", im.size); o.alpha_composite(g); o.alpha_composite(im); im = o
                wx = x - wl if rtl else x
                self.words.append((im, wx - 20, y0 + li * step - f.size * 1.6))
                x = x - wl - sp if rtl else x + wl + sp
        self.t0, self.span, self.t1 = t0, span, t1
    def draw(self, img, t):
        if t < self.t0 or t > self.t1 + 0.6: return
        n = len(self.words)
        out = min(1, ease((self.t1 + 0.6 - t) / 0.6))
        for i, (im, x, y) in enumerate(self.words):
            ts = self.t0 + self.span * i / max(1, n)
            a = ease((t - ts) / 0.35) * out
            if a > 0.01:
                img.alpha_composite(fade(im, a), (int(x), int(y + (1 - ease((t - ts) / 0.35)) * 14)))
