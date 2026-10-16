"""Разное оформление для каждого ролика: палитра + живой фон + орнамент вокруг центра.
Выбор детерминирован по слоту публикации (дата/час в имени файла), соседние ролики не совпадают.
Всё рисуется кодом: без людей и животных, без чужих материалов."""
import hashlib, math, random, re, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import motion as M

W, H = M.W, M.H

# ---------- палитры (тёмные, чтобы светлый текст читался) ----------
PALETTES = [
    ("изумрудная ночь", (4, 10, 9), (9, 26, 21), (233, 190, 140), (196, 206, 198)),
    ("полночь", (3, 6, 16), (12, 22, 48), (232, 198, 142), (190, 200, 222)),
    ("гранат", (14, 4, 7), (44, 11, 18), (238, 200, 150), (222, 200, 196)),
    ("пустынные сумерки", (18, 9, 5), (60, 31, 16), (246, 192, 122), (230, 210, 190)),
    ("бирюза", (2, 12, 14), (6, 40, 46), (236, 206, 150), (186, 214, 210)),
    ("чёрное золото", (5, 5, 5), (24, 21, 16), (226, 186, 112), (205, 200, 190)),
    ("фиалковый рассвет", (9, 6, 18), (38, 22, 56), (242, 202, 168), (212, 200, 226)),
    ("олива", (7, 11, 7), (30, 37, 22), (228, 206, 140), (204, 210, 190)),
]

def gradient(top, bot):
    y = np.linspace(0, 1, H)[:, None]
    g = np.array(top) + (np.array(bot) - np.array(top)) * y[..., None]
    g = np.repeat(g, W, axis=1)
    xx, yy = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
    vig = 1 - 0.55 * np.clip(xx ** 2 * 0.8 + yy ** 2 * 0.6, 0, 1)
    return Image.fromarray((g * vig[..., None]).astype(np.uint8), "RGB").convert("RGBA")

# ---------- живые фоны ----------
class Stars:
    def __init__(self, acc): self.s = M.Stars()
    def draw(self, img, t): self.s.draw(img, t)

class Geometry:
    """Исламская решётка восьмиконечных звёзд, медленно плывёт по диагонали."""
    def __init__(self, acc, tile=240):
        self.tile = tile
        big = Image.new("RGBA", (W + tile * 2, H + tile * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
        col = (*acc, 34)
        for gx in range(0, big.width + tile, tile):
            for gy in range(0, big.height + tile, tile):
                c = (gx, gy); r = tile * 0.42
                for rot in (0, 45):
                    pts = [(c[0] + r * math.cos(math.radians(rot + k * 90)), c[1] + r * math.sin(math.radians(rot + k * 90))) for k in range(4)]
                    d.polygon(pts, outline=col, width=2)
                d.ellipse((c[0] - r * 0.3, c[1] - r * 0.3, c[0] + r * 0.3, c[1] + r * 0.3), outline=(*acc, 22), width=2)
                d.line((gx + tile / 2 - 10, gy + tile / 2, gx + tile / 2 + 10, gy + tile / 2), fill=(*acc, 26), width=2)
        self.big = big
    def draw(self, img, t):
        o = int(t * 14) % self.tile
        img.alpha_composite(self.big.crop((o, o, o + W, o + H)))

class Arches:
    """Туннель из арок михраба: арки медленно надвигаются на зрителя."""
    def __init__(self, acc): self.acc = acc
    def draw(self, img, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        cx, cy = W / 2, H * 0.36
        for k in range(7):
            u = ((k + t * 0.12) % 7) / 7           # 0 — далеко, 1 — близко
            s = 0.08 * math.exp(u * 3.3)
            a = int(70 * min(1, u * 3) * min(1, (1 - u) * 4))
            if a <= 2: continue
            w, h = 520 * s, 900 * s
            pts = []
            for i in range(21):                    # стрельчатый верх
                th = math.pi * i / 20
                x = cx - w / 2 * math.cos(th); y = cy - h * 0.18 - h * 0.32 * math.sin(th) ** 0.8 * (1 + 0.25 * (1 - abs(math.cos(th))))
                pts.append((x, y))
            pts = [(cx - w / 2, cy + h * 0.5)] + pts + [(cx + w / 2, cy + h * 0.5)]
            d.line(pts, fill=(*self.acc, a), width=max(1, int(3 * s ** 0.5)))
        img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(2))); img.alpha_composite(lay)

class Aurora:
    """Мягкие переливающиеся полосы света."""
    def __init__(self, acc):
        self.acc = np.array(acc, float)
        self.xx, self.yy = np.meshgrid(np.linspace(0, 1, 135), np.linspace(0, 1, 240))
    def draw(self, img, t):
        x, y = self.xx, self.yy
        b = np.zeros_like(x)
        for k, (f, sp, y0) in enumerate(((2.2, 0.25, 0.22), (3.1, -0.18, 0.34), (1.6, 0.12, 0.48))):
            c = y0 + 0.05 * np.sin(x * f * 6.28 + t * sp * 2 + k)
            b += np.exp(-((y - c) / 0.05) ** 2) * (0.55 + 0.45 * np.sin(x * 9 + t * 0.6 + k * 2))
        a = np.clip(b * 0.2, 0, 0.3)
        arr = np.zeros((240, 135, 4), np.uint8); arr[..., :3] = self.acc; arr[..., 3] = (a * 255).astype(np.uint8)
        img.alpha_composite(Image.fromarray(arr, "RGBA").resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)))

class Rays:
    """Лучи света сверху, медленно поворачиваются."""
    def __init__(self, acc):
        self.acc = np.array(acc, float)
        xx, yy = np.meshgrid(np.linspace(-1, 1, 180), np.linspace(0, 1.8, 320))
        self.th = np.arctan2(xx, yy + 0.25); self.r = np.sqrt(xx ** 2 + (yy + 0.25) ** 2)
    def draw(self, img, t):
        v = (0.5 + 0.5 * np.sin(self.th * 14 + t * 0.25)) ** 6 * (0.5 + 0.5 * np.sin(self.th * 5 - t * 0.17)) ** 2
        a = np.clip(v * np.exp(-self.r * 1.1) * 0.55, 0, 0.5)
        arr = np.zeros((*a.shape, 4), np.uint8); arr[..., :3] = self.acc; arr[..., 3] = (a * 255).astype(np.uint8)
        img.alpha_composite(Image.fromarray(arr, "RGBA").resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)))

class Bokeh:
    """Крупные мягкие огоньки, плывут вверх."""
    def __init__(self, acc, n=26, seed=3):
        r = random.Random(seed)
        self.sp = [M.glow_sprite(s, acc, 1.2) for s in (40, 70, 110)]
        self.p = [(r.uniform(0, W), r.uniform(0, H), r.randrange(3), r.uniform(0.3, 1.0), r.uniform(0, 6.28)) for _ in range(n)]
    def draw(self, img, t):
        for x, y, k, sp, ph in self.p:
            yy = (y - t * 22 * sp) % (H + 200) - 100
            M.paste_alpha(img, self.sp[k], (x + 30 * math.sin(t * 0.4 + ph), yy), 0.10 + 0.10 * (0.5 + 0.5 * math.sin(t + ph)))

class Rain:
    """Тонкие светлые штрихи падающего дождя."""
    def __init__(self, acc, n=140, seed=5):
        r = random.Random(seed); self.acc = acc
        self.p = [(r.uniform(0, W), r.uniform(0, H), r.uniform(0.6, 1.4), r.uniform(30, 80)) for _ in range(n)]
    def draw(self, img, t):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for x, y, sp, ln in self.p:
            yy = (y + t * 520 * sp) % (H + 100) - 50; xx = (x - t * 60 * sp) % W
            d.line((xx, yy, xx + ln * 0.12, yy - ln), fill=(*self.acc, int(40 * sp)), width=2)
        img.alpha_composite(lay)

class Dunes:
    """Барханы внизу с параллаксом + редкие звёзды сверху."""
    def __init__(self, acc):
        self.acc = acc; self.s = M.Stars(n=120, seed=11)
    def draw(self, img, t):
        self.s.draw(img, t)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        for k, (base, amp, sp, al) in enumerate(((1520, 70, 6, 26), (1640, 90, 12, 34), (1770, 80, 20, 44))):
            pts = [(x, base - amp * (0.6 * math.sin((x + t * sp) / 230 + k) + 0.4 * math.sin((x + t * sp) / 97 + k * 2))) for x in range(0, W + 30, 30)]
            d.polygon(pts + [(W, H), (0, H)], fill=(*self.acc, al))
        img.alpha_composite(lay)

BACKDROPS = [Geometry, Arches, Aurora, Rays, Bokeh, Stars, Dunes, Rain]

# ---------- орнамент вокруг центра ----------
def ornament(style, base, c, t, alpha, acc):
    if alpha <= 0.01: return
    if style == "rings":
        M.draw_rings(base, c, t, alpha, color=acc); return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    col = (*acc, int(150 * alpha))
    if style == "octagram":                       # две вращающиеся квадратные рамки (руб-эль-хизб)
        for i, (r, sp) in enumerate(((200, 8), (262, -5))):
            for rot in (0, 45):
                pts = [(c[0] + r * math.cos(math.radians(rot + t * sp + k * 90)), c[1] + r * math.sin(math.radians(rot + t * sp + k * 90))) for k in range(4)]
                d.polygon(pts, outline=col, width=2)
    elif style == "dots":                         # пунктирные орбиты
        for i, (r, n, sp) in enumerate(((190, 36, 10), (250, 48, -7), (310, 60, 4))):
            for k in range(n):
                a = math.radians(k * 360 / n + t * sp); x, y = c[0] + r * math.cos(a), c[1] + r * math.sin(a)
                s = 3 if k % 6 else 6
                d.ellipse((x - s, y - s, x + s, y + s), fill=(*acc, int((120 if k % 6 else 200) * alpha)))
    elif style == "rosette":                      # 12-лепестковая розетка
        for k in range(12):
            a = math.radians(k * 30 + t * 6)
            p1 = (c[0] + 150 * math.cos(a), c[1] + 150 * math.sin(a))
            for dd in (-1, 1):
                b = a + dd * math.radians(30)
                d.line((p1, (c[0] + 290 * math.cos(b), c[1] + 290 * math.sin(b))), fill=col, width=2)
        d.ellipse((c[0] - 150, c[1] - 150, c[0] + 150, c[1] + 150), outline=(*acc, int(90 * alpha)), width=2)
    base.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3))); base.alpha_composite(lay)

ORNAMENTS = ["rings", "octagram", "dots", "rosette"]

# ---------- центр композиции ----------
def _star_sprite(acc, r=120, k=8):
    s = r * 2 + 40; im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = (s / 2, s / 2)
    pts = []
    for i in range(k * 2):
        rr = r if i % 2 == 0 else r * 0.62; a = math.radians(-90 + i * 180 / k)
        pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    d.polygon(pts, fill=(*acc, 70), outline=(*acc, 230), width=3)
    g = im.filter(ImageFilter.GaussianBlur(10)); out = Image.new("RGBA", im.size); out.alpha_composite(g); out.alpha_composite(im); return out

def _crescent_sprite(acc, r=110):
    s = r * 2 + 60; m = Image.new("L", (s, s), 0); d = ImageDraw.Draw(m); c = s / 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=255); d.ellipse((c - r + 46, c - r - 22, c + r + 46, c + r - 22), fill=0)
    im = Image.new("RGBA", (s, s), (*acc, 0)); im.putalpha(m)
    g = im.filter(ImageFilter.GaussianBlur(14)); out = Image.new("RGBA", im.size); out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(im); return out

def make_center(style, acc):
    orb, core = M.glow_sprite(260, acc, 2.6), M.glow_sprite(40, (255, 245, 220), 1.4)
    if style == "orb":
        def f(img, c, t, g):
            M.paste_alpha(img, orb, c, 0.85 * g, 1 + 0.05 * math.sin(t * 2.4)); M.paste_alpha(img, core, c, min(1, 0.4 + g))
    elif style == "star":
        st = _star_sprite(acc)
        def f(img, c, t, g):
            M.paste_alpha(img, orb, c, 0.55 * g, 1.0)
            sp = st.rotate(t * 9, resample=Image.BICUBIC); M.paste_alpha(img, sp, c, min(1, 0.3 + g), 1 + 0.03 * math.sin(t * 2))
            M.paste_alpha(img, core, c, 0.5 * g)
    elif style == "crescent":
        cr = _crescent_sprite((255, 236, 200))
        def f(img, c, t, g):
            M.paste_alpha(img, orb, c, 0.6 * g, 1 + 0.04 * math.sin(t * 2.0)); M.paste_alpha(img, cr, c, min(1, 0.35 + g), 1 + 0.02 * math.sin(t * 1.6))
    else:  # "halo": кольцо света без шара
        def f(img, c, t, g):
            lay = Image.new("RGBA", (260, 260), (0, 0, 0, 0)); ImageDraw.Draw(lay).ellipse((20, 20, 240, 240), outline=(*acc, 220), width=6)
            gl = lay.filter(ImageFilter.GaussianBlur(9)); o = Image.new("RGBA", lay.size); o.alpha_composite(gl); o.alpha_composite(gl); o.alpha_composite(lay)
            M.paste_alpha(img, orb, c, 0.35 * g, 1.0); M.paste_alpha(img, o, c, min(1, 0.3 + g), 1 + 0.05 * math.sin(t * 1.8)); M.paste_alpha(img, core, c, 0.6 * g, 0.7)
    return f

CENTERS = ["orb", "star", "crescent", "halo"]
INTRO_PARTICLES = ["converge", "burst", "sink"]

def slot_index(out):
    m = re.search(r"(\d{4}-\d{2}-\d{2})[T_](\d{2})", out or "")
    if not m:
        return int(hashlib.md5((out or "x").encode()).hexdigest(), 16) % 9973
    days = (datetime.date.fromisoformat(m.group(1)) - datetime.date(2026, 10, 1)).days
    hr = int(m.group(2)); slots = (9, 12, 15, 18, 21)
    return days * 5 + (slots.index(hr) if hr in slots else hr % 5)

def pick(out):
    """Применяет оформление к модулю motion и возвращает описание."""
    n = slot_index(out)
    pal = PALETTES[n % len(PALETTES)]
    back = BACKDROPS[(n * 3 + 1 + n // len(PALETTES)) % len(BACKDROPS)]
    orn = ORNAMENTS[(n // 2 + n) % len(ORNAMENTS)]
    intro = INTRO_PARTICLES[n % len(INTRO_PARTICLES)]
    cen = CENTERS[(n * 3 + n // 4) % len(CENTERS)]
    name, top, bot, acc, muted = pal
    M.GOLD, M.MUTED = acc, muted
    M.THEME = {"bg": gradient(top, bot), "back": back(acc), "orn": orn, "intro": intro, "acc": acc, "center": make_center(cen, acc)}
    desc = f"оформление: {name} · фон {back.__name__} · орнамент {orn} · центр {cen} · вход {intro}"
    print(desc)
    return desc
