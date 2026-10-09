"""Вертикальное видео ummati (Shorts / Reels / TikTok): сура или аяты с чтением и переводом Кулиева.
Запуск: python video.py 112            -> сура целиком
        python video.py 2:255          -> один аят
        python video.py 103:1-3        -> диапазон
Текст: alquran.cloud (quran-uthmani + ru.kuliev), чтение: Мишари Афаси (cdn.islamic.network).
OFFLINE=dir — взять текст из dir/text.json и тишину вместо чтения (для проверки дизайна)."""
import json, os, sys, subprocess, urllib.request, io, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import render as R

W, H, FPS = 1080, 1920, 30
ACC, FG, MUT = (233, 190, 140), (246, 240, 230), (226, 218, 204)
HERE = os.path.dirname(os.path.abspath(__file__))
AR_FONT = os.environ.get("AR_FONT", os.path.join(HERE, "fonts", "AmiriQuran.woff"))
OFF = os.environ.get("OFFLINE")

def ensure_ar_font():
    if os.path.exists(AR_FONT):
        return
    import tarfile
    os.makedirs(os.path.dirname(AR_FONT), exist_ok=True)
    meta = json.loads(get("https://registry.npmjs.org/@fontsource/amiri-quran/latest"))
    tf = tarfile.open(fileobj=io.BytesIO(get(meta["dist"]["tarball"])))
    open(AR_FONT, "wb").write(tf.extractfile("package/files/amiri-quran-arabic-400-normal.woff").read())

def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()

def load(spec):
    s, _, rng = spec.partition(":")
    if OFF:
        d = json.load(open(os.path.join(OFF, "text.json"), encoding="utf-8"))
    else:
        d = json.loads(get(f"https://api.alquran.cloud/v1/surah/{s}/editions/quran-uthmani,ru.kuliev"))["data"]
        d = {"name": d[1]["englishName"], "ar": [a["text"] for a in d[0]["ayahs"]],
             "ru": [a["text"] for a in d[1]["ayahs"]], "num": [a["number"] for a in d[0]["ayahs"]]}
    a, b = (1, len(d["ar"])) if not rng else (int(rng.split("-")[0]), int(rng.split("-")[-1]))
    ar = d["ar"][a - 1:b]
    if int(s) not in (1, 9) and a == 1:          # в тексте 1-го аята бывает басмала — убираем
        w = ar[0].split()
        if len(w) > 4 and w[0].startswith("بِس"):
            ar[0] = " ".join(w[4:])
    ru = [t.replace(" - ", " — ").strip() for t in d["ru"][a - 1:b]]
    return int(s), d["name"], a, ar, ru, d["num"][a - 1:b]

def audio(nums, work):
    files, durs = [], []
    for i, n in enumerate(nums):
        f = os.path.join(work, f"a{i}.mp3")
        if OFF:
            dur = json.load(open(os.path.join(OFF, "text.json")))["dur"][i]
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                            "-t", str(dur), f], check=True)
        else:
            open(f, "wb").write(get(f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{n}.mp3"))
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f],
                           capture_output=True, text=True, check=True)
        files.append(f); durs.append(float(p.stdout.strip()))
    return files, durs

def wrap(d, text, f, maxw, rtl=False):
    words, lines, cur = text.split(), [], ""
    kw = {"direction": "rtl"} if rtl else {}
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f, **kw) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def spaced(d, y, text, f, fill, sp):
    total = sum(d.textlength(c, font=f) for c in text) + sp * (len(text) - 1)
    x = (W - total) / 2
    for c in text:
        d.text((x, y), c, font=f, fill=fill); x += d.textlength(c, font=f) + sp

def orn(d, y, a=200):
    cx = W / 2
    d.line([cx - 110, y, cx - 26, y], fill=(*ACC, a), width=2)
    d.line([cx + 26, y, cx + 110, y], fill=(*ACC, a), width=2)
    d.polygon([(cx, y - 9), (cx + 9, y), (cx, y + 9), (cx - 9, y)], outline=(*ACC, 255))

def ayah_layer(ar, ru, ref, idx, total):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    n = len(ar)
    fa = ImageFont.truetype(AR_FONT, 104 if n < 40 else 90 if n < 80 else 74 if n < 140 else 62,
                            layout_engine=ImageFont.Layout.RAQM)
    m = len(ru)
    fr = R.font("CormorantGaramond_500Medium.ttf", 64 if m < 50 else 56 if m < 100 else 48 if m < 170 else 42)
    fs = R.font("Montserrat_600SemiBold.ttf", 24)
    al = wrap(d, ar, fa, W - 180, rtl=True)
    rl = wrap(d, ru, fr, W - 200)
    alh, rlh = int(fa.size * 1.75), int(fr.size * 1.18)
    block = len(al) * alh + 70 + len(rl) * rlh + 60 + 30
    y = 980 - block // 2
    for ln in al:
        d.text((W / 2, y + alh // 2), ln, font=fa, fill=(*ACC, 255), anchor="mm", direction="rtl"); y += alh
    y += 34; orn(d, y); y += 36
    for ln in rl:
        d.text(((W - d.textlength(ln, font=fr)) / 2, y), ln, font=fr, fill=(*FG, 255)); y += rlh
    y += 40
    spaced(d, y, ref.upper(), fs, (*ACC, 230), 5)
    # точки прогресса
    if total > 1:
        r, gap = 7, 30; x0 = W / 2 - gap * (total - 1) / 2
        for i in range(total):
            c = (*ACC, 255) if i == idx else (*FG, 70)
            d.ellipse([x0 + i * gap - r, 1560 - r, x0 + i * gap + r, 1560 + r], fill=c)
    return L

def chrome_layer(title):
    """Постоянные элементы: логотип и название суры сверху."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    import ig_render
    lg = ig_render._logo(FG, 170)
    L.alpha_composite(lg, ((W - lg.width) // 2, 150))
    spaced(d, 150 + lg.height + 40, title.upper(), R.font("Montserrat_600SemiBold.ttf", 25), (*ACC, 255), 8)
    return L

def outro_layer(offer):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    import ig_render
    lg = ig_render._logo(FG, 300)
    L.alpha_composite(lg, ((W - lg.width) // 2, 640))
    y = 640 + lg.height + 70
    ft = R.font("CormorantGaramond_500Medium.ttf", 66)
    for ln in ["Сохраните и отправьте", "тому, кому это нужно"]:
        d.text(((W - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=(*FG, 255)); y += 78
    y += 50; orn(d, y); y += 60
    fb = R.font("Montserrat_400Regular.ttf", 34)
    for ln in offer:
        d.text(((W - d.textlength(ln, font=fb)) / 2, y), ln, font=fb, fill=(*MUT, 255)); y += 52
    return L

def background(photo, total_frames):
    ph = Image.open(photo).convert("RGB")
    s = max(W * 1.12 / ph.width, H * 1.12 / ph.height)
    ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(5))
    dark = Image.new("RGB", ph.size, (10, 22, 18))
    ph = Image.blend(ph, dark, 0.62)
    # виньетка
    v = Image.new("L", ph.size, 0); vd = ImageDraw.Draw(v)
    for i in range(60):
        k = i / 60
        vd.rectangle([int(ph.width * k * 0.25), int(ph.height * k * 0.2), ph.width - int(ph.width * k * 0.25),
                      ph.height - int(ph.height * k * 0.2)], fill=int(255 * k))
    v = v.filter(ImageFilter.GaussianBlur(80))
    ph = Image.composite(ph, Image.blend(ph, dark, 0.6), v)
    def frame(i):
        z = 1 + 0.06 * i / max(1, total_frames)          # медленный наезд
        cw, ch = W * 1.12 / z, H * 1.12 / z
        cx, cy = ph.width / 2, ph.height / 2
        return ph.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((W, H), Image.BILINEAR)
    return frame

def build(spec, photo, out, offer=("Намазные коврики ummati", "Акция 1+1: 2 коврика за 9 900 ₸")):
    R.ensure_fonts(); ensure_ar_font()
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "_work"); os.makedirs(work, exist_ok=True)
    s, name, a, ar, ru, nums = load(spec)
    files, durs = audio(nums, work)
    intro, gap, outro, fade = 0.8, 0.5, 3.5, 0.35
    names = {1: "Аль-Фатиха", 103: "Аль-Аср", 108: "Аль-Каусар", 112: "Аль-Ихлас", 113: "Аль-Фаляк", 114: "Ан-Нас"}
    title = f"Сура «{names.get(s, name)}»"
    # таймлайн: (начало, конец, слой)
    scenes, t = [], 0.0
    for i, (x, y, dur) in enumerate(zip(ar, ru, durs)):
        start = t; t += (intro if i == 0 else 0) + dur + gap
        scenes.append((start, t, ayah_layer(x, y, f"Коран, {s}:{a + i} · пер. Э. Кулиева", i, len(ar))))
    scenes.append((t, t + outro, outro_layer(offer)))
    total = t + outro
    # звук: пауза intro, аяты с паузами gap, тишина в конце
    parts = []
    for i, f in enumerate(files):
        parts += [f"-i", f]
    flt = "".join(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={int((intro if i == 0 else 0) * 1000)}|{int((intro if i == 0 else 0) * 1000)},apad=pad_dur={gap}[a{i}];"
                  for i in range(len(files)))
    flt += "".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1,apad=whole_dur={total}[aout]"
    wav = os.path.join(work, "voice.m4a")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *parts, "-filter_complex", flt, "-map", "[aout]",
                    "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "160k", wav], check=True)
    chrome = chrome_layer(title)
    nf = int(total * FPS)
    bg = background(photo, nf)
    enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                            "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", "-movflags", "+faststart", out],
                           stdin=subprocess.PIPE)
    for fi in range(nf):
        tt = fi / FPS
        img = bg(fi).convert("RGBA")
        last = len(scenes) - 1
        ot = scenes[last][0]
        ca = 1.0 if tt < ot - fade else max(0.0, (ot - tt) / fade)
        if ca > 0: img.alpha_composite(chrome if ca >= 1 else fade_l(chrome, ca))
        for k, (st, en, lay) in enumerate(scenes):
            al = min(1.0, (tt - st) / fade + (1.0 if st == 0 else 0))
            if k < last: al = min(al, (en - tt) / fade)
            if al > 0: img.alpha_composite(lay if al >= 1 else fade_l(lay, al))
        enc.stdin.write(img.convert("RGB").tobytes())
    enc.stdin.close(); enc.wait()
    ref = f"{s}" if len(ar) > 1 and a == 1 else f"{s}:{a}" + (f"-{a + len(ar) - 1}" if len(ar) > 1 else "")
    meta = {"title": f"{title} — чтение и перевод смыслов #shorts" if len(ar) > 1 or a == 1 else f"Коран, {ref} — чтение и перевод смыслов #shorts",
            "description": " ".join(ru) + f"\n\nКоран, {ref}. Перевод смыслов: Э. Кулиев. Чтец: Мишари Рашид аль-Афаси.\n\n"
                           "Ummati — намазные коврики. Акция 1+1: 2 коврика за 9 900 ₸, вода Зам-Зам, тасбих и подарочная упаковка в комплекте. "
                           "Instagram: @ummati.family\n\n#коран #ислам #намаз #сура #shorts"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return total

def fade_l(layer, a):
    r, g, b, al = layer.split()
    return Image.merge("RGBA", (r, g, b, al.point(lambda v: int(v * a))))

if __name__ == "__main__":
    spec = sys.argv[1] if len(sys.argv) > 1 else "112"
    photo = sys.argv[2] if len(sys.argv) > 2 else "green_tex.jpg"
    out = sys.argv[3] if len(sys.argv) > 3 else "short.mp4"
    print("Готово:", out, f"{build(spec, photo, out):.1f} c")
