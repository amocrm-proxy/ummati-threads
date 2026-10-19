"""Уағыз: нарезка законченных по смыслу отрывков (до 60 с) в вертикальные ролики 1080x1920 для Instagram Reels.
python uagyz/cut.py <видео> <clips.json> <папка_вывода>
clips.json: {"ustaz": "Имя устаза", "clips": [{"id": "01", "start": 123.4, "end": 170.2}, ...]}
Границы подравниваются по словам из transcript.json (рядом с clips.json), чтобы не резать слово пополам.
Кадр: говорящий по центру (обрезка 4:5) на размытом фоне того же видео, сверху — имя устаза, снизу — Ummati."""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
GOLD, CREAM = (233, 190, 140), (246, 240, 230)
FG_Y = 330                                   # видео 1080x1350: 330–1680, имя сверху, бренд снизу

def font(name, size):
    for p in (os.path.join(ROOT, "fonts", name), os.path.join(ROOT, name)):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def snap(t, words, side):
    """Подровнять время к границе слова: начало — к началу ближайшего слова, конец — к концу."""
    if not words:
        return t
    if side == "start":
        c = min(words, key=lambda w: abs(w[0] - t)); return max(0.0, c[0] - 0.25)
    c = min(words, key=lambda w: abs(w[1] - t)); return c[1] + 0.45

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w_
    return lines + ([cur] if cur else [])

def overlay(ustaz, path, top, bottom, kicker="УАҒЫЗ", topic=""):
    """top — верх видео, bottom — низ видео: тема ролика крупно над видео (видна и в сетке профиля), имя устаза, бренд под видео."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f1 = font("Montserrat_600SemiBold.ttf", 32 if ustaz else 40); f2 = font("CormorantGaramond_500Medium.ttf", 76)
    if topic:                                    # тема ролика — главный заголовок, чтобы ролики в профиле различались
        ft = font("CormorantGaramond_500Medium.ttf", 92)
        lines = wrap(d, topic, ft, W - 140)
        if len(lines) > 2:
            ft = font("CormorantGaramond_500Medium.ttf", 74); lines = wrap(d, topic, ft, W - 120)
        lh = int(ft.size * 1.08); y = top - 60 - lh * len(lines)
        sub = (kicker + " · " + ustaz) if ustaz else kicker
        fs = font("Montserrat_600SemiBold.ttf", 28); sp = 5
        w = sum(d.textlength(c, font=fs) for c in sub) + sp * (len(sub) - 1); x = (W - w) / 2
        for c in sub:
            d.text((x, y - 58), c, font=fs, fill=(*GOLD, 255)); x += d.textlength(c, font=fs) + sp
        for ln in lines:
            d.text(((W - d.textlength(ln, font=ft)) / 2, y), ln, font=ft, fill=(*CREAM, 255)); y += lh
    elif ustaz:
        d.text(((W - d.textlength(kicker, font=f1)) / 2, top - 175), kicker, font=f1, fill=(*GOLD, 255))
        d.text(((W - d.textlength(ustaz, font=f2)) / 2, top - 128), ustaz, font=f2, fill=(*CREAM, 255))
    else:                                        # без имени (подкаст, несколько устазов) — только заголовок рубрики
        sp = 10; w = sum(d.textlength(c, font=f1) for c in kicker) + sp * (len(kicker) - 1); x = (W - w) / 2
        for c in kicker:
            d.text((x, top - 100), c, font=f1, fill=(*GOLD, 255)); x += d.textlength(c, font=f1) + sp
    f3 = font("Montserrat_600SemiBold.ttf", 30); f4 = font("Montserrat_400Regular.ttf", 32)
    b1 = "UMMATI · ЖАЙНАМАЗДАР"; d.text(((W - d.textlength(b1, font=f3)) / 2, bottom + 60), b1, font=f3, fill=(*GOLD, 255))
    b2 = "@ummati.family"; d.text(((W - d.textlength(b2, font=f4)) / 2, bottom + 108), b2, font=f4, fill=(*CREAM, 230))
    im.save(path)

def cut(src, a, b, ustaz, out, work, cx=0.5, layout="full", kicker="УАҒЫЗ", topic=""):
    """layout=full — весь кадр 16:9 по ширине (безопасно при смене планов камеры), crop — обрезка 4:5 вокруг cx."""
    png = os.path.join(work, "overlay.png")
    if layout == "crop":
        fg_h, y = 1350, FG_Y
        fg = f"crop='min(iw,ih*4/5)':ih:'max(0,min(iw-min(iw,ih*4/5),iw*{cx}-min(iw,ih*4/5)/2))':0,scale={W}:{fg_h},setsar=1"
    else:
        fg_h = 608; y = (H - fg_h) // 2
        fg = f"scale={W}:{fg_h},setsar=1"
    overlay(ustaz, png, y, y + fg_h, kicker, topic)
    vf = (f"[0:v]split[bg0][fg0];"
          f"[bg0]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=30:2,eq=brightness=-0.25[bg];"
          f"[fg0]{fg}[fg];"
          f"[bg][fg]overlay=0:{y}[v0];[v0][1:v]overlay=0:0,format=yuv420p[v]")
    dur = b - a
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{a:.2f}", "-t", f"{dur:.2f}", "-i", src, "-i", png,
                    "-filter_complex", vf + f";[0:a]afade=t=in:d=0.15,afade=t=out:st={max(0, dur - 0.35):.2f}:d=0.35,loudnorm=I=-14:TP=-1.5[a]",
                    "-map", "[v]", "-map", "[a]", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out], check=True)

if __name__ == "__main__":
    src, cfg_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    cfg = json.load(open(cfg_p, encoding="utf-8"))
    tp = os.path.join(os.path.dirname(cfg_p), "transcript.json")
    words = [w for s in json.load(open(tp, encoding="utf-8"))["segments"] for w in s["words"]] if os.path.exists(tp) else []
    for c in cfg["clips"]:
        a, b = snap(float(c["start"]), words, "start"), snap(float(c["end"]), words, "end")
        if b - a > 60:
            b = a + 60
        out = os.path.join(outdir, f"{c['id']}.mp4")
        cut(src, a, b, cfg.get("ustaz", ""), out, outdir, float(cfg.get("crop_x", 0.5)), cfg.get("layout", "full"),
            cfg.get("kicker", "УАҒЫЗ"), c.get("topic", ""))
        print("Ролик", c["id"], f"{a:.1f}–{b:.1f}", f"({b - a:.1f} с)")
