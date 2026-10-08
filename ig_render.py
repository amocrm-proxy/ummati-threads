"""Слайды и сторис ummati для Instagram (на базе render.py)."""
import base64, io
from PIL import Image, ImageDraw, ImageFilter
import render as R

LOGO = None

def _logo(rgb, w):
    mask = Image.open(io.BytesIO(base64.b64decode(R.LOGO_MASK))).convert("L")
    lg = Image.new("RGBA", mask.size, rgb); lg.putalpha(mask)
    return lg.resize((w, int(lg.height * w / lg.width)), Image.LANCZOS)

def _canvas(pal, w, h):
    R.W, R.H = w, h
    return R.background(R.PALETTES[pal])

def _frame(d, a, w, h):
    d.rounded_rectangle([44, 44, w - 44, h - 44], 6, outline=(*a, 115), width=2)
    d.rounded_rectangle([56, 56, w - 56, h - 56], 4, outline=(*a, 56), width=1)

def _orn(d, a, cx, y):
    d.line([cx - 105, y + 7, cx - 25, y + 7], fill=(*a, 150), width=2)
    d.line([cx + 25, y + 7, cx + 105, y + 7], fill=(*a, 150), width=2)
    d.polygon([(cx, y - 2), (cx + 9, y + 7), (cx, y + 16), (cx - 9, y + 7)], outline=(*a, 255))

def _spaced(d, w, y, text, f, fill, sp):
    total = sum(d.textlength(c, font=f) for c in text) + sp * (len(text) - 1)
    x = (w - total) / 2
    for c in text:
        d.text((x, y), c, font=f, fill=fill); x += d.textlength(c, font=f) + sp

def text_slide(pal, kicker, title=None, body=None, quote=None, source=None, page=None, story=False, footer=None):
    """Текстовый слайд: kicker, крупный заголовок/цитата, текст. story=True -> 1080x1920."""
    R.ensure_fonts()
    w, h = (1080, 1920) if story else (1080, 1350)
    p = R.PALETTES[pal]; a = p["acc"]
    img = _canvas(pal, w, h)
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    _frame(d, a, w, h)
    fk = R.font("Montserrat_600SemiBold.ttf", 22 if story else 21)
    big = quote or title
    n = len(big or "")
    if quote:
        qs = 92 if n < 40 else 80 if n < 60 else 70 if n < 90 else 60 if n < 150 else 52
        fb = R.font("CormorantGaramond_500Medium.ttf", qs + (8 if story else 0)); big = "«" + quote + "»"
    else:
        qs = 88 if n < 30 else 74 if n < 55 else 62 if n < 90 else 54
        fb = R.font("CormorantGaramond_500Medium.ttf", qs + (8 if story else 0))
    fe = R.font("Montserrat_400Regular.ttf", 34 if story else 31)
    fs = R.font("Montserrat_600SemiBold.ttf", 21)
    blines = R.wrap(d, big, fb, w - 220) if big else []
    elines = []
    for para in (body or "").split("\n"):
        elines += R.wrap(d, para, fe, w - 280) if para.strip() else [""]
    blh = int(fb.size * 1.12); elh = int(fe.size * 1.5)
    block = 22 + 26 + 48 + len(blines) * blh + (47 + 48 if source else 0) + (30 + len(elines) * elh if elines else 0)
    top, bottom = (230, h - 300) if story else (130, h - 190)
    y = top + max(0, (bottom - top - block) // 2)
    if kicker:
        _spaced(d, w, y, kicker.upper(), fk, (*a, 255), 9); y += 48
        _orn(d, a, w / 2, y); y += 48
    for ln in blines:
        d.text(((w - d.textlength(ln, font=fb)) / 2, y), ln, font=fb, fill=(*p["fg"], 255)); y += blh
    if source:
        y += 26; _spaced(d, w, y, source.upper(), fs, (*a, 255), 5); y += 21 + 26
        _orn(d, a, w / 2, y); y += 48
    else:
        y += 30
    for ln in elines:
        d.text(((w - d.textlength(ln, font=fe)) / 2, y), ln, font=fe, fill=p["mut"]); y += elh
    if page:
        fp = R.font("Montserrat_600SemiBold.ttf", 20)
        d.text((w - 110 - d.textlength(page, font=fp), 92), page, font=fp, fill=(*a, 200))
    if footer:
        ff = R.font("Montserrat_600SemiBold.ttf", 30)
        tw = d.textlength(footer, font=ff)
        y0 = h - (330 if story else 250)
        d.rounded_rectangle([(w - tw) / 2 - 40, y0, (w + tw) / 2 + 40, y0 + 76], 38, fill=(*a, 255))
        d.text(((w - tw) / 2, y0 + 20), footer, font=ff, fill=(*p["bg2"], 255))
    img = Image.alpha_composite(img, ov)
    lg = _logo(p["logo_rgb"], 140 if not story else 170)
    img.alpha_composite(lg, ((w - lg.width) // 2, h - (82 if not story else 120) - lg.height))
    return img.convert("RGB")

def photo_slide(photo_path, title, sub=None, page=None, story=False, footer=None, kicker=None):
    """Фото на весь кадр + затемнение снизу + подпись."""
    R.ensure_fonts()
    w, h = (1080, 1920) if story else (1080, 1350)
    ph = Image.open(photo_path).convert("RGB")
    s = max(w / ph.width, h / ph.height)
    ph = ph.resize((int(ph.width * s) + 1, int(ph.height * s) + 1), Image.LANCZOS)
    l, t = (ph.width - w) // 2, (ph.height - h) // 2
    img = ph.crop((l, t, l + w, t + h)).convert("RGBA")
    grad = Image.new("RGBA", (w, h), (0, 0, 0, 0)); gd = ImageDraw.Draw(grad)
    g0 = int(h * (0.5 if story else 0.52))
    for y in range(g0, h):
        k = (y - g0) / (h - g0)
        gd.line([(0, y), (w, y)], fill=(12, 24, 20, int(235 * min(1, k * 1.25))))
    top_h = 220
    for y in range(0, top_h):
        gd.line([(0, y), (w, y)], fill=(12, 24, 20, int(110 * (1 - y / top_h))))
    img = Image.alpha_composite(img, grad)
    d = ImageDraw.Draw(img)
    acc, fg = (233, 164, 123), (246, 240, 230)
    ft = R.font("CormorantGaramond_500Medium.ttf", 84 if story else 76)
    fsb = R.font("Montserrat_400Regular.ttf", 34 if story else 31)
    fk = R.font("Montserrat_600SemiBold.ttf", 22)
    tl = R.wrap(d, title, ft, w - 160)
    sl = []
    for para in (sub or "").split("\n"):
        sl += R.wrap(d, para, fsb, w - 180) if para.strip() else []
    bottom = h - (330 if story else 110) - (110 if footer else 0)
    y = bottom - len(tl) * int(ft.size * 1.08) - len(sl) * int(fsb.size * 1.45) - (60 if kicker else 0) - (20 if sl else 0)
    if kicker:
        _spaced(d, w, y, kicker.upper(), fk, acc, 9); y += 60
    for ln in tl:
        d.text(((w - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=fg); y += int(ft.size * 1.08)
    y += 20
    for ln in sl:
        d.text(((w - d.textlength(ln, font=fsb)) / 2, y), ln, font=fsb, fill=(246, 240, 230, 220)); y += int(fsb.size * 1.45)
    if footer:
        ff = R.font("Montserrat_600SemiBold.ttf", 30)
        tw = d.textlength(footer, font=ff); y0 = y + 34
        d.rounded_rectangle([(w - tw) / 2 - 40, y0, (w + tw) / 2 + 40, y0 + 76], 38, fill=acc)
        d.text(((w - tw) / 2, y0 + 20), footer, font=ff, fill=(23, 50, 42))
    lg = _logo((246, 240, 230), 150 if story else 120)
    img.alpha_composite(lg, ((w - lg.width) // 2, 80 if story else 60))
    if page:
        fp = R.font("Montserrat_600SemiBold.ttf", 20)
        d.text((w - 70 - d.textlength(page, font=fp), 70), page, font=fp, fill=(246, 240, 230))
    return img.convert("RGB")
