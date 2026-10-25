"""Shorts / Reels «Сүннет» и «Әдеп»: короткие действия из сунны (только то, что есть и у Бұхари, и у Муслима),
без цитат хадисов. Тексты — sunnet_kk.json (проверены Арсеном 25/10/2026). Звук — тихая природа (sfx/), без чтения.
python sunnet_video.py sunna|adab out.mp4"""
import json, os, random, subprocess, sys
from PIL import ImageDraw
import render as R
import card

W, H = card.W, card.H
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "sunnet_state.json")
CARDS = json.load(open(os.path.join(HERE, "sunnet_kk.json"), encoding="utf-8"))
KICK = {"sunna": "СҮННЕТ", "adab": "ӘДЕП"}
BEDS = ["forest_stream", "wind_trees", "small_stream", "forest", "summer_rain", "night_rain", "birds_city"]
FG, ACC, MUT = card.FG, card.ACC, card.MUT

def pick(cat):
    pool = [c for c in CARDS if c["cat"] == cat]
    st = json.load(open(STATE)) if os.path.exists(STATE) else {}
    i = int(st.get(cat, 0))
    st[cat] = i + 1
    json.dump(st, open(STATE, "w"))
    return pool[i % len(pool)], i

def image(c, photo, cat):
    R.ensure_fonts()
    img = card.photo_bg(photo)
    w, hh = img.size
    d = ImageDraw.Draw(img)
    dy = (hh - H) // 2
    fk = R.font("Montserrat_600SemiBold.ttf", 30)
    k = KICK[cat]
    tw = d.textlength(k, font=fk) + len(k) * 8
    x = (w - tw) / 2
    for ch in k:
        d.text((x, dy + 430), ch, font=fk, fill=ACC); x += d.textlength(ch, font=fk) + 8
    ft = R.font("CormorantGaramond_500Medium.ttf", 76)
    n = sum(len(s) for s in c["lines"])
    fl = R.font("Montserrat_400Regular.ttf", 44 if n < 120 else 38)
    tl = R.wrap(d, c["title"], ft, W - 180)
    ll = []
    for s in c["lines"]:
        part = R.wrap(d, s, fl, W - 220)
        ll.append(part)
    lh = int(fl.size * 1.35)
    block = len(tl) * 88 + 50 + sum(len(p) * lh + 26 for p in ll) + 90
    y = dy + 520 + max(0, (1000 - block) // 2)
    for ln in tl:
        d.text(((w - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=FG); y += 88
    y += 50
    for p in ll:
        for j, ln in enumerate(p):
            s = ("• " if j == 0 and len(c["lines"]) > 1 else "") + ln
            d.text(((w - d.textlength(s, font=fl)) / 2, y), s, font=fl, fill=MUT); y += lh
        y += 26
    fs = R.font("Montserrat_400Regular.ttf", 30)
    src = f"({c['src']})"
    d.text(((w - d.textlength(src, font=fs)) / 2, y + 40), src, font=fs, fill=ACC)
    import ig_render
    lg = ig_render._logo(ACC, 150)
    img.alpha_composite(lg, ((w - lg.width) // 2, dy + 1650))
    return img.convert("RGB")

def bed(idx):
    have = [b for b in BEDS if os.path.exists(os.path.join(HERE, "sfx", b + ".mp3"))]
    return os.path.join(HERE, "sfx", have[idx % len(have)] + ".mp3") if have else None

def build(cat, out):
    c, idx = pick(cat)
    n = len(c["title"]) + sum(len(s) for s in c["lines"])
    total = max(9.0, min(22.0, n / 11 + 5))
    work = out.rsplit(".", 1)[0] + "_sunnet"
    os.makedirs(work, exist_ok=True)
    png = os.path.join(work, "card.png")
    image(c, card.PHOTOS[idx % len(card.PHOTOS)], cat).save(png)
    frames = int(total * 30)
    vf = (f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=30,"
          f"fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.2f}:d=0.8")
    b = bed(idx + (0 if cat == "sunna" else 3))
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
    tag = "#сүннет" if cat == "sunna" else "#әдеп"
    body = "\n".join("• " + s for s in c["lines"])
    meta = {"title": f"{c['title']} — {KICK[cat].capitalize()} #shorts",
            "description": f"{c['title']}\n{body}\n({c['src']})\n\nUmmati — жайнамаздар. Instagram: @ummati.family\n\n{tag} #сүннет #ислам #shorts",
            "caption": f"{tag} #сүннет #ислам"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Сүннет:", cat, c["title"])
    return total

if __name__ == "__main__":
    print("Готово:", build(sys.argv[1], sys.argv[2]))
