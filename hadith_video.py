"""Shorts / TikTok «Хадис дня»: текст хадиса дословно (hadiths.json, перевод HadeethEnc.com) на фоне фото,
звук — тихая природа (CC0, BigSoundBank, папка sfx/). Чтения Корана нет — нечему попадать под Content ID.
Хадисы идут по кругу (hadith_state.json), только короткие — чтобы текст успевали прочитать.
python hadith_video.py out.mp4"""
import json, os, random, re, subprocess, sys
from PIL import ImageDraw
import render as R
import content as C
import card

W, H = card.W, card.H
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "hadith_state.json")
BEDS = ["forest_stream", "wind_trees", "small_stream", "forest", "summer_rain", "night_rain", "birds_city"]
FG, ACC, MUT = card.FG, card.ACC, card.MUT

def pool():
    out = []
    for h in C.hadiths():
        intro, body = C.hadith_parts(h)
        if 30 <= len(body) <= 260 and len(intro) <= 170 and h.get("grade"):
            out.append(h)
    return out

def pick():
    P = pool()
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"i": 0}
    i = int(st.get("i", 0))
    json.dump({"i": i + 1}, open(STATE, "w"))
    return P[i % len(P)], i

def image(h, photo):
    R.ensure_fonts()
    intro, body = C.hadith_parts(h)
    img = card.photo_bg(photo)
    w, hh = img.size
    d = ImageDraw.Draw(img)
    dx, dy = (w - W) // 2, (hh - H) // 2
    fk = R.font("Montserrat_600SemiBold.ttf", 30)
    k = "ХАДИС ДНЯ"
    tw = d.textlength(k, font=fk) + len(k) * 6
    x = (w - tw) / 2; y = dy + 420
    for ch in k:
        d.text((x, y), ch, font=fk, fill=ACC); x += d.textlength(ch, font=fk) + 6
    n = len(body)
    size = 70 if n < 90 else 62 if n < 150 else 56 if n < 210 else 50
    fq = R.font("CormorantGaramond_500Medium.ttf", size)
    fi = R.font("Montserrat_400Regular.ttf", 32)
    il = R.wrap(d, intro, fi, W - 220) if intro else []
    ql = R.wrap(d, body, fq, W - 180)
    lh, ilh = int(size * 1.2), 44
    block = len(il) * ilh + (30 if il else 0) + len(ql) * lh
    y = dy + 520 + max(0, (1000 - block) // 2)
    for ln in il:
        d.text(((w - d.textlength(ln, font=fi)) / 2, y), ln, font=fi, fill=MUT); y += ilh
    y += 30 if il else 0
    for ln in ql:
        d.text(((w - d.textlength(ln, font=fq)) / 2, y), ln, font=fq, fill=FG); y += lh
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    fs = R.font("Montserrat_400Regular.ttf", 30)
    y += 40
    for ln in R.wrap(d, f"{attr} · {h['grade']}", fs, W - 220):
        d.text(((w - d.textlength(ln, font=fs)) / 2, y), ln, font=fs, fill=ACC); y += 42
    import ig_render
    lg = ig_render._logo(ACC, 150)
    img.alpha_composite(lg, ((w - lg.width) // 2, dy + 1650))
    return img.convert("RGB")

def bed(idx):
    have = [b for b in BEDS if os.path.exists(os.path.join(HERE, "sfx", b + ".mp3"))]
    if not have:
        return None
    return os.path.join(HERE, "sfx", have[idx % len(have)] + ".mp3")

def build(out):
    h, idx = pick()
    intro, body = C.hadith_parts(h)
    print("Хадис:", h["id"], body[:80])
    total = max(10.0, min(24.0, (len(intro) + len(body)) / 13 + 3))
    work = out.rsplit(".", 1)[0] + "_hadith"
    os.makedirs(work, exist_ok=True)
    png = os.path.join(work, "card.png")
    image(h, card.PHOTOS[idx % len(card.PHOTOS)]).save(png)
    frames = int(total * 30)
    vf = (f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.2f}:d=0.8")
    b = bed(idx)
    if b:
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", b],
                                   capture_output=True, text=True, check=True).stdout.strip())
        ss = random.Random(idx).uniform(0, max(0.0, dur - total - 1))
        ain = ["-ss", f"{ss:.1f}", "-i", b]
        af = f"[1:a]aresample=44100,aformat=channel_layouts=stereo,afade=t=in:d=1.2,afade=t=out:st={total - 1.5:.2f}:d=1.5,loudnorm=I=-24:TP=-3,apad[a]"
    else:
        ain = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        af = "[1:a]anull[a]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, *ain,
                    "-filter_complex", f"[0:v]{vf}[v];{af}", "-map", "[v]", "-map", "[a]",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    q = re.findall(r"[«“]([^«»“”]{15,})[»”]", body)   # в заголовок — последние слова в кавычках (обычно слова Пророка)
    m = bool(q)
    core = q[-1].strip() if q else body
    short = core if len(core) <= 70 else core[:core.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
    short = f"«{short}»" if m else short
    meta = {"title": f"{short} — хадис #shorts",
            "description": (intro + "\n" if intro else "") + body + f"\n\n{attr}. {h['grade']}.\n"
                           "Перевод: Энциклопедия переведённых пророческих хадисов (HadeethEnc.com).\n\n"
                           "Ummati — намазные коврики. Акция 1+1: 2 коврика за 9 900 ₸, вода Зам-Зам, тасбих и подарочная упаковка в комплекте. "
                           "Instagram: @ummati.family\n\n#хадис #сунна #ислам #пророк #shorts"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return total

if __name__ == "__main__":
    print("Готово:", build(sys.argv[1] if len(sys.argv) > 1 else "hadith.mp4"))
