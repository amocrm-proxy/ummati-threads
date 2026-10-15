"""Вертикальное видео ummati (Shorts / Reels / TikTok): сура или аяты с чтением и переводом Кулиева.
Запуск: python video.py 112            -> сура целиком
        python video.py 2:255          -> один аят
        python video.py 103:1-3        -> диапазон
Текст: alquran.cloud (quran-uthmani + ru.kuliev), чтение: cdn.islamic.network (чтец — READER, Алафаси не берём: Content ID).
OFFLINE=dir — взять текст из dir/text.json и тишину вместо чтения (для проверки дизайна)."""
import json, os, sys, subprocess, urllib.request, io, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import render as R

W, H, FPS = 1080, 1920, 30
ACC, FG, MUT = (233, 190, 140), (246, 240, 230), (226, 218, 204)
HERE = os.path.dirname(os.path.abspath(__file__))
AR_FONT = os.environ.get("AR_FONT", os.path.join(HERE, "fonts", "AmiriQuran.woff"))
OFF = os.environ.get("OFFLINE")
NAMES = ["Аль-Фатиха", "Аль-Бакара", "Али Имран", "Ан-Ниса", "Аль-Маида", "Аль-Анам", "Аль-Араф", "Аль-Анфаль", "Ат-Тауба", "Юнус", "Худ", "Юсуф", "Ар-Раад", "Ибрахим", "Аль-Хиджр", "Ан-Нахль", "Аль-Исра", "Аль-Кахф", "Марьям", "Та Ха", "Аль-Анбия", "Аль-Хадж", "Аль-Муминун", "Ан-Нур", "Аль-Фуркан", "Аш-Шуара", "Ан-Намль", "Аль-Касас", "Аль-Анкабут", "Ар-Рум", "Лукман", "Ас-Саджда", "Аль-Ахзаб", "Саба", "Фатыр", "Ясин", "Ас-Саффат", "Сад", "Аз-Зумар", "Гафир", "Фуссылят", "Аш-Шура", "Аз-Зухруф", "Ад-Духан", "Аль-Джасия", "Аль-Ахкаф", "Мухаммад", "Аль-Фатх", "Аль-Худжурат", "Каф", "Аз-Зарият", "Ат-Тур", "Ан-Наджм", "Аль-Камар", "Ар-Рахман", "Аль-Вакиа", "Аль-Хадид", "Аль-Муджадаля", "Аль-Хашр", "Аль-Мумтахана", "Ас-Сафф", "Аль-Джумуа", "Аль-Мунафикун", "Ат-Тагабун", "Ат-Талак", "Ат-Тахрим", "Аль-Мульк", "Аль-Калям", "Аль-Хакка", "Аль-Мааридж", "Нух", "Аль-Джинн", "Аль-Муззаммиль", "Аль-Муддассир", "Аль-Кияма", "Аль-Инсан", "Аль-Мурсалят", "Ан-Наба", "Ан-Назиат", "Абаса", "Ат-Таквир", "Аль-Инфитар", "Аль-Мутаффифин", "Аль-Иншикак", "Аль-Бурудж", "Ат-Тарик", "Аль-Аля", "Аль-Гашия", "Аль-Фаджр", "Аль-Балад", "Аш-Шамс", "Аль-Лейл", "Ад-Духа", "Аш-Шарх", "Ат-Тин", "Аль-Алак", "Аль-Кадр", "Аль-Баййина", "Аз-Зальзаля", "Аль-Адият", "Аль-Кариа", "Ат-Такасур", "Аль-Аср", "Аль-Хумаза", "Аль-Филь", "Курайш", "Аль-Маун", "Аль-Каусар", "Аль-Кафирун", "Ан-Наср", "Аль-Масад", "Аль-Ихлас", "Аль-Фаляк", "Ан-Нас"]
# порядок Shorts: сначала короткие суры целиком, потом аяты из bank.json (целые, без обрезки)
SURAS = ["112", "113", "114", "1", "103", "108", "110", "106", "105", "107", "111", "109", "102", "104", "95", "94", "97", "99", "100", "101", "2:255"]
PHOTOS = ["green_tex.jpg", "brown_tex.jpg", "L1033130.jpg"]
START = "2026-10-11"
READERS = {"ar.husary": "Махмуд Халиль аль-Хусари", "ar.abdulsamad": "Абдуль-Басит Абдус-Самад",
           "ar.muhammadayyoub": "Мухаммад Айюб"}
READER = "ar.husary"                          # 09:00 — Хусари, 18:00 — Абдуль-Басит (см. __main__)

COUNTS = [7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99, 128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60, 34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38, 29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18, 12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29, 19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8, 11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6]

def locate(n):
    """Сквозной номер аята 1..6236 -> (сура, аят)."""
    for s, c in enumerate(COUNTS, 1):
        if n <= c:
            return s, n
        n -= c
    return 1, 1

def auto_spec(slot=None):
    """Следующий отрывок Корана по порядку (yt_state.json): аяты одной суры, примерно до 50 секунд чтения.
    Новое значение пишется в yt_state.json — workflow сохраняет его только после успешной загрузки на YouTube."""
    st = json.load(open(os.path.join(HERE, "yt_state.json"))) if os.path.exists(os.path.join(HERE, "yt_state.json")) else {"next": 1}
    n = (int(st.get("next", 1)) - 1) % sum(COUNTS) + 1
    s, a = locate(n)
    d = json.loads(get(f"https://api.alquran.cloud/v1/surah/{s}/quran-uthmani"))["data"]["ayahs"]
    b, total = a, len(d[a - 1]["text"])
    while b < COUNTS[s - 1] and b - a < 11 and total + len(d[b]["text"]) <= 650:
        total += len(d[b]["text"]); b += 1
    json.dump({"next": n + (b - a + 1)}, open(os.path.join(HERE, "yt_state.json"), "w"))
    return f"{s}:{a}-{b}", PHOTOS[n % len(PHOTOS)]

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
            open(f, "wb").write(get(f"https://cdn.islamic.network/quran/audio/{64 if READER == 'ar.abdulsamad' else 128}/{READER}/{n}.mp3"))
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

CMAP = None
def clean_ar(t):
    """Убираем символы, которых нет в шрифте (иначе на экране будут квадраты)."""
    global CMAP
    if CMAP is None:
        try:
            from fontTools.ttLib import TTFont
            CMAP = set(TTFont(AR_FONT).getBestCmap())
        except Exception:
            CMAP = set()
    return "".join(ch for ch in t if not CMAP or ch.isspace() or ord(ch) in CMAP)

def ayah_layer(ar, ru, ref, idx, total):
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    ar = clean_ar(ar)
    n, m = len(ar), len(ru)
    sa = 104 if n < 40 else 90 if n < 80 else 74 if n < 140 else 62
    sr = 64 if m < 50 else 56 if m < 100 else 48 if m < 170 else 42
    fs = R.font("Montserrat_600SemiBold.ttf", 24)
    for _ in range(10):                          # уменьшаем шрифт, пока текст не влезет между шапкой и точками
        fa = ImageFont.truetype(AR_FONT, sa, layout_engine=ImageFont.Layout.RAQM)
        fr = R.font("CormorantGaramond_500Medium.ttf", sr)
        al = wrap(d, ar, fa, W - 180, rtl=True)
        rl = wrap(d, ru, fr, W - 200)
        alh, rlh = int(fa.size * (1.75 if len(al) < 3 else 1.6)), int(fr.size * 1.18)
        block = len(al) * alh + 70 + len(rl) * rlh + 60 + 30
        if block <= 1180:
            break
        sa, sr = int(sa * 0.9), max(30, int(sr * 0.92))
    y = max(370, 990 - block // 2)
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
            d.ellipse([x0 + i * gap - r, 1640 - r, x0 + i * gap + r, 1640 + r], fill=c)
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

def pages_of(ar, ru, limit=330):
    """Длинный аят -> части [(арабский, русский)]: русский режем по предложениям, арабский — пропорционально по словам."""
    if len(ru) <= limit + 60:
        return [(ar, ru)]
    import content
    rp = content.chunks(ru, limit)
    rp = [content.show(p, i, len(rp)) for i, p in enumerate(rp)]
    words, total, out, used_w = ar.split(), sum(len(p) for p in rp), [], 0
    acc = 0
    for i, p in enumerate(rp):
        acc += len(p)
        upto = len(words) if i == len(rp) - 1 else max(used_w + 1, round(len(words) * acc / total))
        out.append((" ".join(words[used_w:upto]), p)); used_w = upto
    return out

def voice_layer(ru, ref):
    """Кадр, пока звучит голос автора: «Размышление» + перевод смыслов аята."""
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    m = len(ru); fr = R.font("CormorantGaramond_500Medium.ttf", 64 if m < 80 else 54 if m < 160 else 46 if m < 260 else 40)
    rl = wrap(d, ru, fr, W - 200); rlh = int(fr.size * 1.2)
    y = max(420, 980 - (len(rl) * rlh + 160) // 2)
    spaced(d, y, "РАЗМЫШЛЕНИЕ", R.font("Montserrat_600SemiBold.ttf", 26), (*ACC, 255), 9); y += 50
    orn(d, y); y += 50
    for ln in rl:
        d.text(((W - d.textlength(ln, font=fr)) / 2, y), ln, font=fr, fill=(*FG, 255)); y += rlh
    spaced(d, y + 36, ref.upper(), R.font("Montserrat_600SemiBold.ttf", 24), (*ACC, 230), 5)
    return L

def build(spec, photo, out, offer=("Намазные коврики ummati", "Акция 1+1: 2 коврика за 9 900 ₸"), voice=None):
    R.ensure_fonts(); ensure_ar_font()
    work = os.path.join(os.path.dirname(os.path.abspath(out)), "_work"); os.makedirs(work, exist_ok=True)
    s, name, a, ar, ru, nums = load(spec)
    files, durs = audio(nums, work)
    intro, gap, outro, fade = 0.8, 0.5, 3.5, 0.35
    title = f"Сура «{NAMES[s - 1]}»"
    # таймлайн: (начало, конец, слой)
    scenes, t = [], 0.0
    if voice:                                           # сначала голос автора, потом чтение
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
                           capture_output=True, text=True, check=True)
        t = intro + float(p.stdout.strip()) + gap
        scenes.append((0.0, t, voice_layer(" ".join(ru) if len(" ".join(ru)) < 300 else ru[0],
                                           f"Коран, {s}:{a}" + (f"-{a + len(ar) - 1}" if len(ar) > 1 else ""))))
        files = [voice] + files
    for i, (x, y, dur) in enumerate(zip(ar, ru, durs)):
        ref_i = f"Коран, {s}:{a + i} · пер. Э. Кулиева"
        pages = pages_of(x, y)
        t += intro if i == 0 and not voice else 0
        for j, (px, py) in enumerate(pages):           # длинный аят показываем по частям, пока звучит чтение
            start = t if (i or j or voice) else 0.0
            t += dur * len(py) / max(1, sum(len(q) for _, q in pages)) + (gap if j == len(pages) - 1 else 0)
            scenes.append((start, t, ayah_layer(px, py, ref_i + (f" · {j + 1}/{len(pages)}" if len(pages) > 1 else ""), i, len(ar))))
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
    whole = a == 1 and a + len(ar) - 1 == COUNTS[s - 1]
    ref = f"{s}" if whole else f"{s}:{a}" + (f"-{a + len(ar) - 1}" if len(ar) > 1 else "")
    part = "" if whole else (f", аят {a}" if len(ar) == 1 else f", аяты {a}–{a + len(ar) - 1}")
    smysl = ""
    try:                                              # краткий смысл первого аята (тафсир ас-Саади, пер. Э. Кулиева)
        import content
        t = content.tafsir(s, a)
        if t:
            smysl = f"Смысл: {t[0]}\n({t[1]}, перевод Э. Кулиева, сокращено)\n\n"
    except Exception as e:
        print("тафсир:", e)
    meta = {"title": f"{title}{part} — " + ("размышление и чтение" if voice else "чтение и перевод смыслов") + " #shorts",
            "description": " ".join(ru) + f"\n\nКоран, {ref}. Перевод смыслов: Э. Кулиев. Чтец: {READERS[READER]}.\n\n" + smysl +
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
    voice = None
    if spec.startswith("voice:"):                       # voice:2:286 -> карточка аята + голос автора (voices/2_286.ogg)
        import card
        ref = spec[6:]
        print("Готово:", out, f"{card.build_voice(ref, os.path.join(HERE, 'voices', ref.replace(':', '_') + '.ogg'), out):.1f} c")
        sys.exit(0)
    elif spec.startswith("support"):                    # support:… -> «Слова поддержки»: аят (с чтением) или хадис утешения
        import support, card, hadith_video
        stf = os.path.join(HERE, "support_state.json")
        k = json.load(open(stf)).get("i", 0) if os.path.exists(stf) else 0
        for j in range(k, k + 10):                      # берём ближайший, который помещается на экран
            x = support.item(j)
            if not x:
                continue
            if x[0] == "ayah" and len(x[3]) <= 300:
                total = card.build(out, given=x[1:], kicker=support.KICKER); break
            if x[0] == "hadith" and sum(map(len, support.C.hadith_parts(x[1]))) <= 400:
                total = hadith_video.build(out, h=x[1], kicker=support.KICKER, idx=j); break
        else:
            raise SystemExit("Нет подходящего текста для «Слов поддержки»")
        json.dump({"i": j + 1}, open(stf, "w"))
        print("Готово:", out, f"{total:.1f} c"); sys.exit(0)
    elif spec.startswith("hadith"):                     # hadith:… -> «Хадис дня»: текст хадиса + звуки природы
        import hadith_video
        print("Готово:", out, f"{hadith_video.build(out):.1f} c"); sys.exit(0)
    elif spec.startswith("card"):                       # card:… -> «Сильный аят»: картинка + чтение (card.py)
        import card
        print("Готово:", out, f"{card.build(out):.1f} c"); sys.exit(0)
    elif spec.startswith("auto"):
        if spec[16:18] == "18":                         # auto:2026-10-13T18 — вечерний отрывок читает Абдуль-Басит
            READER = "ar.abdulsamad"
        spec, photo = auto_spec(spec[5:] or None)
        print("Сегодня:", spec, photo)
    print("Готово:", out, f"{build(spec, photo, out, voice=voice):.1f} c")
