"""Shorts «Сильный аят»: одна картинка 10–20 секунд + чтение Мишари Афаси.
Аяты — целые аяты из bank.json по кругу (card_state.json), только короткие (перевод до ~190 знаков).
Текст — дословно перевод Кулиева из alquran.cloud, своими словами не пишем.
python card.py out.mp4   (вызывается из video.py для spec «card»)"""
import json, os, subprocess, sys, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import render as R
import content as C

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "card_state.json")
PHOTOS = ["L1033120.jpg", "green_tex.jpg", "brown_tex.jpg", "L1033130.jpg", "black_rect.jpg", "green_label.jpg"]
MAXLEN = 190
FG, ACC, MUT = (246, 240, 230), (233, 190, 140), (226, 218, 204)

def pick():
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"i": 0}
    bank = [b["ref"] for b in json.load(open(os.path.join(HERE, "bank.json"), encoding="utf-8")) if not b.get("q")]
    i = int(st.get("i", 0))
    for k in range(40):                           # ищем следующий короткий аят
        ref = bank[(i + k) % len(bank)]
        d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev")
        if not d or d["data"]["edition"]["identifier"] != "ru.kuliev":
            continue
        text = d["data"]["text"].replace(" - ", " — ").strip()
        if len(text) <= MAXLEN:
            json.dump({"i": i + k + 1}, open(STATE, "w"))
            return ref, text, d["data"]["number"], d["data"]["surah"]["number"], d["data"]["numberInSurah"], i + k
    raise SystemExit("Не нашёл короткий аят")

def photo_bg(name):
    p = os.path.join(HERE, name)
    if not os.path.exists(p):
        p = os.path.join(HERE, "green_tex.jpg")
    im = Image.open(p).convert("RGB")
    s = max(W * 1.12 / im.width, H * 1.12 / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    l, t = (im.width - int(W * 1.12)) // 2, (im.height - int(H * 1.12)) // 2
    im = im.crop((l, t, l + int(W * 1.12), t + int(H * 1.12))).filter(ImageFilter.GaussianBlur(3))
    im = ImageEnhance.Brightness(im).enhance(0.42)
    ov = Image.new("RGBA", im.size, (8, 20, 16, 120))
    return Image.alpha_composite(im.convert("RGBA"), ov)

def card_image(text, s, a, photo, kicker=None):
    """Кадр 1210x2150 (с запасом под медленный наезд камеры)."""
    R.ensure_fonts()
    img = photo_bg(photo)
    w, h = img.size
    d = ImageDraw.Draw(img)
    dx, dy = (w - W) // 2, (h - H) // 2
    fk = R.font("Montserrat_600SemiBold.ttf", 30)
    sura = kicker or f"СУРА {s} · {C.NAMES[s - 1].upper()}"
    tw = d.textlength(sura, font=fk) + len(sura) * 6
    x = (w - tw) / 2; y = dy + 600
    for ch in sura:
        d.text((x, y), ch, font=fk, fill=ACC); x += d.textlength(ch, font=fk) + 6
    fa = R.font("Montserrat_400Regular.ttf", 30)
    ref = f"Коран, {s}:{a}" if kicker else f"аят {a}"
    d.text(((w - d.textlength(ref, font=fa)) / 2, y + 48), ref, font=fa, fill=MUT)
    n = len(text)
    size = 86 if n < 60 else 76 if n < 100 else 66 if n < 140 else 58
    fq = R.font("CormorantGaramond_500Medium.ttf", size)
    lines = R.wrap(d, text, fq, W - 200)
    lh = int(size * 1.18)
    y = dy + 820 + max(0, (560 - len(lines) * lh) // 2)
    for ln in lines:
        d.text(((w - d.textlength(ln, font=fq)) / 2, y), ln, font=fq, fill=FG); y += lh
    fs = R.font("Montserrat_400Regular.ttf", 28)
    note = "Перевод смыслов Э. Кулиева"
    d.text(((w - d.textlength(note, font=fs)) / 2, dy + 1560), note, font=fs, fill=(*MUT, 200))
    import ig_render
    lg = ig_render._logo(ACC, 150)
    img.alpha_composite(lg, ((w - lg.width) // 2, dy + 1650))
    return img.convert("RGB")

def build(out):
    ref, text, num, s, a, idx = pick()
    print("Сильный аят:", ref, text)
    work = out.rsplit(".", 1)[0] + "_card"
    os.makedirs(work, exist_ok=True)
    mp3 = os.path.join(work, "a.mp3")
    with urllib.request.urlopen(f"https://cdn.islamic.network/quran/audio/128/ar.alafasy/{num}.mp3", timeout=60) as r:
        open(mp3, "wb").write(r.read())
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                               capture_output=True, text=True, check=True).stdout.strip())
    total = max(10.0, dur + 2.0)
    png = os.path.join(work, "card.png")
    card_image(text, s, a, PHOTOS[idx % len(PHOTOS)]).save(png)
    frames = int(total * 30)
    vf = (f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.2f}:d=0.8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", mp3,
                    "-filter_complex", f"[0:v]{vf}[v];[1:a]adelay=700|700,apad[a]", "-map", "[v]", "-map", "[a]",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    smysl = ""
    try:
        t = C.tafsir(s, a)
        if t:
            smysl = f"Смысл: {t[0]}\n({t[1]}, перевод Э. Кулиева, сокращено)\n\n"
    except Exception as e:
        print("тафсир:", e)
    short = text if len(text) <= 70 else text[:text.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
    meta = {"title": f"«{short}» — Коран {s}:{a} #shorts",
            "description": f"«{text}»\n\nКоран, сура «{C.NAMES[s - 1]}», аят {a}. Перевод смыслов: Э. Кулиев. "
                           "Чтец: Мишари Рашид аль-Афаси.\n\n" + smysl +
                           "Ummati — намазные коврики. Акция 1+1: 2 коврика за 9 900 ₸, вода Зам-Зам, тасбих и подарочная упаковка в комплекте. "
                           "Instagram: @ummati.family\n\n#коран #ислам #аят #намаз #shorts"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return total

def build_voice(ref, voice, out):
    """«Размышление»: карточка аята + голос автора (без чужого чтения — никаких заявок по авторским правам)."""
    d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev")
    if not d or d["data"]["edition"]["identifier"] != "ru.kuliev":
        raise SystemExit("Нет перевода Кулиева")
    text = d["data"]["text"].replace(" - ", " — ").strip()
    s, a = d["data"]["surah"]["number"], d["data"]["numberInSurah"]
    work = out.rsplit(".", 1)[0] + "_voice"
    os.makedirs(work, exist_ok=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", voice],
                               capture_output=True, text=True, check=True).stdout.strip())
    total = dur + 2.0
    shown = text if len(text) <= 260 else text[:text.rfind(" ", 0, 250)].rstrip(",;:—-") + "…"
    png = os.path.join(work, "card.png")
    card_image(shown, s, a, PHOTOS[a % len(PHOTOS)], kicker="РАЗМЫШЛЕНИЕ").save(png)
    frames = int(total * 30)
    vf = (f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.2f}:d=0.8")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", voice,
                    "-filter_complex", f"[0:v]{vf}[v];[1:a]adelay=700|700,loudnorm=I=-16:TP=-1.5,apad[a]",
                    "-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out],
                   check=True)
    smysl = ""
    t = C.tafsir(s, a)
    if t:
        smysl = f"Смысл: {t[0]}\n({t[1]}, перевод Э. Кулиева, сокращено)\n\n"
    meta = {"title": f"Размышление над аятом {s}:{a} — сура «{C.NAMES[s - 1]}» #shorts",
            "description": f"«{text}»\n\nКоран, сура «{C.NAMES[s - 1]}», аят {a}. Перевод смыслов: Э. Кулиев.\n\n" + smysl +
                           "Рубрика «Размышление» от Ummati: каждый день один аят и мысль о том, как применить его сегодня.\n\n"
                           "Ummati — намазные коврики. Instagram: @ummati.family\n\n#коран #ислам #аят #размышление #shorts"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return total

if __name__ == "__main__":
    print("Готово:", build(sys.argv[1] if len(sys.argv) > 1 else "card.mp4"))
