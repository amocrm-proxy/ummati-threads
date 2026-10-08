"""Отрисовка карточки ummati 1080x1350 (PIL). render(quote, source, explain, hour) -> PIL.Image"""
import math, os, urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
NPM = {
    "Montserrat_400Regular.ttf": "https://registry.npmjs.org/@expo-google-fonts/montserrat/-/montserrat-0.2.3.tgz",
    "Montserrat_600SemiBold.ttf": "https://registry.npmjs.org/@expo-google-fonts/montserrat/-/montserrat-0.2.3.tgz",
    "CormorantGaramond_500Medium.ttf": "https://registry.npmjs.org/@expo-google-fonts/cormorant-garamond/-/cormorant-garamond-0.2.3.tgz",
}

def ensure_fonts():
    import tarfile, io
    os.makedirs(FONT_DIR, exist_ok=True)
    cache = {}
    for name, url in NPM.items():
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            continue
        if url not in cache:
            cache[url] = urllib.request.urlopen(url, timeout=60).read()
        with tarfile.open(fileobj=io.BytesIO(cache[url])) as t:
            open(p, "wb").write(t.extractfile("package/" + name).read())

PALETTES = {
    "night": dict(bg=(21, 42, 46), bg2=(11, 23, 25), fg=(238, 240, 234), acc=(217, 176, 126), mut=(238, 240, 234, 184), logo_rgb=(233, 164, 123)),
    "cream": dict(bg=(244, 237, 226), bg2=(234, 223, 207), fg=(29, 53, 44), acc=(184, 105, 63), mut=(29, 53, 44, 190), logo_rgb=(29, 53, 44)),
    "emer":  dict(bg=(23, 50, 42), bg2=(15, 36, 30), fg=(246, 240, 230), acc=(233, 164, 123), mut=(246, 240, 230, 184), logo_rgb=(233, 164, 123)),
    "choc":  dict(bg=(58, 33, 25), bg2=(38, 20, 15), fg=(246, 237, 226), acc=(226, 176, 122), mut=(246, 237, 226, 184), logo_rgb=(233, 164, 123)),
}

def palette_for_hour(h):
    if 6 <= h <= 11: return "cream"
    if 12 <= h <= 17: return "emer"
    if 18 <= h <= 20: return "choc"
    return "night"

def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

def wrap(draw, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def spaced(draw, xy_center_y, text, f, fill, spacing):
    total = sum(draw.textlength(c, font=f) for c in text) + spacing * (len(text) - 1)
    x = (W - total) / 2
    for c in text:
        draw.text((x, xy_center_y), c, font=f, fill=fill)
        x += draw.textlength(c, font=f) + spacing

def background(p):
    img = Image.new("RGB", (W, H), p["bg2"])
    px = img.load()
    cx, cy = W / 2, H * 0.4
    for y in range(H):
        for x in range(0, W):
            d = min(1, math.hypot((x - cx) / (W * 0.75), (y - cy) / (H * 0.7)))
            t = max(0, (d - 0.45) / 0.55)
            px[x, y] = tuple(int(p["bg"][i] * (1 - t) + p["bg2"][i] * t) for i in range(3))
    # узор: восьмиконечные звёзды, гаснут к центру
    pat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pat)
    a = p["acc"]
    for gy in range(0, H + 120, 120):
        for gx in range(0, W + 120, 120):
            d = math.hypot((gx + 60 - cx) / (W * 0.6), (gy + 60 - cy) / (H * 0.6))
            alpha = int(max(0, min(1, (d - 0.35) / 0.5)) * 30)
            if not alpha: continue
            c = (*a, alpha)
            x0, y0 = gx + 38, gy + 38
            pd.rectangle([x0, y0, x0 + 44, y0 + 44], outline=c, width=2)
            r = 31
            pts = [(gx + 60 + r * math.cos(math.radians(k)), gy + 60 + r * math.sin(math.radians(k))) for k in (0, 90, 180, 270)]
            pd.polygon(pts, outline=c)
    img = Image.alpha_composite(img.convert("RGBA"), pat)
    return img

def render(quote, source, explain, hour, kicker="СЛОВА ВСЕВЫШНЕГО"):
    ensure_fonts()
    p = PALETTES[palette_for_hour(hour)]
    img = background(p)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    a = p["acc"]
    d.rounded_rectangle([44, 44, W - 44, H - 44], 6, outline=(*a, 115), width=2)
    d.rounded_rectangle([56, 56, W - 56, H - 56], 4, outline=(*a, 56), width=1)

    n = len(quote)
    qs = 92 if n < 40 else 80 if n < 60 else 68 if n < 85 else 58 if n < 150 else 50
    fq = font("CormorantGaramond_500Medium.ttf", qs)
    fk = font("Montserrat_600SemiBold.ttf", 21)
    fs = font("Montserrat_600SemiBold.ttf", 21)
    fe = font("Montserrat_400Regular.ttf", 30)
    qlines = wrap(d, "«" + quote + "»", fq, 840)
    elines = wrap(d, explain, fe, 780)
    qlh, elh = int(qs * 1.1), 45
    block = 21 + 26 + 14 + 34 + len(qlines) * qlh + 30 + 21 + 26 + 14 + 34 + len(elines) * elh
    top, bottom = 130, H - 180
    y = top + max(0, (bottom - top - block) // 2)

    spaced(d, y, kicker, fk, (*a, 255), 9); y += 21 + 26
    def orn(y):
        cx = W / 2
        d.line([cx - 105, y + 7, cx - 25, y + 7], fill=(*a, 150), width=2)
        d.line([cx + 25, y + 7, cx + 105, y + 7], fill=(*a, 150), width=2)
        d.polygon([(cx, y - 2), (cx + 9, y + 7), (cx, y + 16), (cx - 9, y + 7)], outline=(*a, 255))
    orn(y); y += 14 + 34
    for ln in qlines:
        tw = d.textlength(ln, font=fq)
        d.text(((W - tw) / 2, y), ln, font=fq, fill=(*p["fg"], 255)); y += qlh
    y += 30
    spaced(d, y, source.upper(), fs, (*a, 255), 5); y += 21 + 26
    orn(y); y += 14 + 34
    for ln in elines:
        tw = d.textlength(ln, font=fe)
        d.text(((W - tw) / 2, y), ln, font=fe, fill=p["mut"]); y += elh

    img = Image.alpha_composite(img, ov)
    import base64, io
    mask = Image.open(io.BytesIO(base64.b64decode(LOGO_MASK))).convert("L")
    logo = Image.new("RGBA", mask.size, p["logo_rgb"]); logo.putalpha(mask)
    lw = 140; logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
    img.alpha_composite(logo, ((W - lw) // 2, H - 82 - logo.height))
    return img.convert("RGB")

LOGO_MASK = "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"

if __name__ == "__main__":
    import sys
    render("Господи! Раскрой для меня мою грудь! Облегчи мою миссию!", "Коран, 20:25–26",
           "С этим дуа пророк Муса шёл к фараону. Читайте его перед экзаменом, важной встречей или трудным разговором.",
           int(sys.argv[1]) if len(sys.argv) > 1 else 13).save("test.jpg", quality=92)
