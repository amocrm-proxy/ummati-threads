"""Светлый стиль «Рукопись» для хадисов: кремовая бумага, тёмно-зелёные «чернила», рамка рисуется сама,
слова проявляются как чернила (из размытия в резкость). Тексты — дословно, своих толкований нет."""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import motion as M
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kk

W, H = M.W, M.H
PAPER, PAPER_EDGE = (242, 237, 227), (222, 212, 194)
INK, GREEN, SOFT = (28, 54, 43), (62, 120, 96), (120, 116, 104)
GOLD = (176, 138, 74)
HERE = os.path.dirname(os.path.abspath(__file__))

def paper():
    rng = np.random.default_rng(4)
    yy, xx = np.meshgrid(np.linspace(-1, 1, H), np.linspace(-1, 1, W), indexing="ij")
    v = np.clip(xx ** 2 * 0.7 + yy ** 2 * 0.5, 0, 1)[..., None]
    base = np.array(PAPER) * (1 - v) + np.array(PAPER_EDGE) * v
    n = rng.normal(0, 1, (H // 4, W // 4))
    n = np.array(Image.fromarray(((n - n.min()) / (n.max() - n.min()) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC), float) / 255 - 0.5
    fib = rng.normal(0, 1, (H, W)) * 2.2
    img = np.clip(base + n[..., None] * 9 + fib[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(img, "RGB").convert("RGBA")
    # водяной знак: восьмиконечные звёзды
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); tile = 270
    for gx in range(0, W + tile, tile):
        for gy in range(0, H + tile, tile):
            for rot in (0, 45):
                r = tile * 0.36
                d.polygon([(gx + r * math.cos(math.radians(rot + k * 90)), gy + r * math.sin(math.radians(rot + k * 90))) for k in range(4)],
                          outline=(*GREEN, 16), width=2)
    im.alpha_composite(lay)
    return im

class Dust:
    def __init__(self, n=40, seed=2):
        r = random.Random(seed); self.p = [(r.uniform(0, W), r.uniform(0, H), r.uniform(1, 3), r.uniform(0.3, 1), r.uniform(0, 6)) for _ in range(n)]
    def draw(self, img, t):
        d = ImageDraw.Draw(img)
        for x, y, s, sp, ph in self.p:
            yy = (y - t * 14 * sp) % H; xx = x + 20 * math.sin(t * 0.5 + ph)
            d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(*GOLD, int(70 + 50 * math.sin(t + ph))))

def frame_path(inset=64, r=40):
    pts = []; x0, y0, x1, y1 = inset, inset, W - inset, H - inset
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(10):
            a = math.radians(a0 + k * 9); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    # старт сверху по центру
    i0 = 0; pts = [(W / 2, y0)] + pts[:] + [pts[0], (W / 2, y0)]
    return pts

def draw_partial(d, pts, frac, fill, width):
    if frac <= 0: return
    L = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; tot = sum(L); goal = tot * min(1, frac)
    acc = 0; out = [pts[0]]
    for i, l in enumerate(L):
        if acc + l >= goal:
            u = (goal - acc) / l; out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * u, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * u)); break
        out.append(pts[i + 1]); acc += l
    d.line(out, fill=fill, width=width, joint="curve")

def star8(d, c, r, fill):
    pts = []
    for i in range(16):
        rr = r if i % 2 == 0 else r * 0.45; a = math.radians(-90 + i * 22.5); pts.append((c[0] + rr * math.cos(a), c[1] + rr * math.sin(a)))
    d.polygon(pts, fill=fill)

class Ink:
    """Слова проявляются как чернила: из размытия в резкость, по порядку чтения."""
    def __init__(self, text, f, color, y, t0, span, t1, maxw=880, lh=1.32):
        tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        lines = M.wrap(text, f, maxw, tmp); step = int(f.size * lh)
        y0 = y - step * len(lines) / 2 + f.size
        self.w = []
        for li, ln in enumerate(lines):
            full = tmp.textlength(ln, font=f); x = (W - full) / 2; sp = tmp.textlength(" ", font=f)
            for wd in ln.split():
                wl = tmp.textlength(wd, font=f)
                im = Image.new("RGBA", (int(wl) + 40, int(f.size * 2.2)), (0, 0, 0, 0))
                ImageDraw.Draw(im).text((20, int(f.size * 1.5)), wd, font=f, fill=color, anchor="ls")
                self.w.append((im, im.filter(ImageFilter.GaussianBlur(7)), x - 20, y0 + li * step - f.size * 1.5))
                x += wl + sp
        self.t0, self.span, self.t1 = t0, span, t1
        self.bottom = y0 + step * len(lines)
    def draw(self, img, t):
        if t < self.t0 or t > self.t1 + 0.6: return
        out = min(1, M.ease((self.t1 + 0.6 - t) / 0.6)); n = len(self.w)
        for i, (im, bl, x, y) in enumerate(self.w):
            ts = self.t0 + self.span * i / max(1, n); u = (t - ts) / 0.5
            if u <= 0: continue
            a = M.ease(u) * out
            if u < 1: img.alpha_composite(M.fade(bl, (1 - M.ease(u)) * 0.7 * out), (int(x), int(y)))
            img.alpha_composite(M.fade(im, a), (int(x), int(y)))

def tblock(s, f, col, maxw=880, spacing=0):
    return M.text_block(s, f, col, maxw=maxw, spacing=spacing)

def hadith(out, kicker, intro, body, source, bed=None):
    import auto, ig_render
    nw = len(body.split()); read = nw / 2.5
    t_body = 2.2 if intro else 1.6
    t_src = t_body + read + 0.5
    e0 = t_src + 3.0; total = e0 + 3.8
    audio = None
    if bed and os.path.exists(bed):
        audio = out.rsplit(".", 1)[0] + "_bed.m4a"; auto.mix([], total, audio, bed=bed, bed_vol=0.6)
    bg = paper(); dust = Dust(); fpath = frame_path()
    size = 72 if len(body) < 120 else 64 if len(body) < 220 else 56 if len(body) < 320 else 48
    fb = M.SERIF(size); fi = M.SANS(32)
    k_img = tblock(kicker, M.SANS_B(36), GREEN, spacing=8)
    hi = auto.block_h(intro, fi, 860) if intro else 0
    hb = auto.block_h(body, fb, 880, lh=1.32)
    top = 960 - (hi + hb) / 2
    intro_w = Ink(intro, fi, SOFT, top + hi / 2, 0.9, 0.9, e0 - 0.3, maxw=860) if intro else None
    yb = top + hi + (36 if intro else 0)
    body_w = Ink(body, fb, INK, yb + hb / 2, t_body, read, e0 - 0.3)
    ys = body_w.bottom + 40
    src = M.Item(tblock(source, M.SANS(28), GREEN), ys + 40, t_src, e0, rise=16)
    save = M.Item(tblock(kk.SAVE if kk.ON else "СОХРАНИТЕ И ОТПРАВЬТЕ БЛИЗКИМ", M.SANS(24), SOFT, spacing=4), ys + 110, t_src + 0.7, e0, rise=12)
    logo = ig_render._logo(INK, 230)
    end_t = M.Item(tblock(kk.BRAND if kk.ON else "UMMATI · НАМАЗНЫЕ КОВРИКИ", M.SANS(26), GREEN, spacing=5), 1130, e0 + 0.6, total)

    def scene(img, t):
        dust.draw(img, t)
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        draw_partial(d, fpath, M.ease(t / 2.2), (*GREEN, 220), 4)
        inner = [(x if x == W / 2 else (x + 16 if x < W / 2 else x - 16), y + (16 if y < H / 2 else -16)) for x, y in fpath]
        draw_partial(d, inner, M.ease((t - 0.3) / 2.2), (*GOLD, 170), 2)
        for c in ((64, 64), (W - 64, 64), (64, H - 64), (W - 64, H - 64)):
            a = M.ease((t - 1.6) / 0.6)
            if a > 0: star8(d, c, 16, (*GOLD, int(200 * a)))
        # заголовок + разделитель, рисующийся от центра
        a = M.ease((t - 0.2) / 0.6) * (1 - M.ease((t - e0 + 0.3) / 0.5))
        if a > 0:
            img.alpha_composite(M.fade(k_img, a), ((W - k_img.width) // 2, 330 - k_img.height // 2))
            u = M.ease((t - 0.4) / 1.0); half = 220 * u
            d.line((W / 2 - half, 400, W / 2 - 22, 400), fill=(*GOLD, int(200 * a)), width=2)
            d.line((W / 2 + 22, 400, W / 2 + half, 400), fill=(*GOLD, int(200 * a)), width=2)
            star8(d, (W / 2, 400), 13 * u, (*GOLD, int(230 * a)))
        img.alpha_composite(lay)
        if intro_w: intro_w.draw(img, t)
        body_w.draw(img, t)
        src.draw(img, t); save.draw(img, t)
        a = M.ease((t - e0 - 0.1) / 0.8)
        if a > 0:
            img.alpha_composite(M.fade(logo, a), ((W - logo.width) // 2, 860 - logo.height // 2 + int((1 - a) * 20)))
        end_t.draw(img, t)

    class Back:  # бумага + ничего (пыль рисуется в сцене)
        def draw(self, img, t): pass
    M.THEME = {"bg": bg, "back": Back()}
    M.render(scene, out, total, audio)
    return total

def cover(out_png, kicker, headline, sub=None):
    """Обложка Reels 1080x1920; ключевое — в центральной зоне 1080x1440 (сетка профиля)."""
    img = paper(); d = ImageDraw.Draw(img)
    fpath = frame_path(); draw_partial(d, fpath, 1, (*GREEN, 220), 4)
    for c in ((64, 64), (W - 64, 64), (64, H - 64), (W - 64, H - 64)): star8(d, c, 16, (*GOLD, 200))
    k = tblock(kicker, M.SANS_B(40), GREEN, spacing=10); img.alpha_composite(k, ((W - k.width) // 2, 420))
    d.line((W / 2 - 220, 520, W / 2 - 24, 520), fill=(*GOLD, 220), width=3); d.line((W / 2 + 24, 520, W / 2 + 220, 520), fill=(*GOLD, 220), width=3)
    star8(d, (W / 2, 520), 15, (*GOLD, 240))
    hl = M.text_block(headline, M.SERIF(104), INK, maxw=860, lh=1.12)
    y = max(600, 860 - hl.height // 2); img.alpha_composite(hl, ((W - hl.width) // 2, y))
    if sub:
        s = tblock(sub, M.SANS(30), SOFT, spacing=3); img.alpha_composite(s, ((W - s.width) // 2, y + hl.height + 30))
    import ig_render
    lg = ig_render._logo(INK, 150); img.alpha_composite(lg, ((W - lg.width) // 2, 1380))
    img.convert("RGB").save(out_png, quality=93)
