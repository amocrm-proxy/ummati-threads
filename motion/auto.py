"""Моушн-ролики на поток (стиль «Аль-Аср»): аяты под чтение, хадис, слова поддержки, продажа коврика.
Тексты аятов — дословно (quran-uthmani + ru.kuliev, загружаются из alquran.cloud), хадисы — дословно из hadiths.json.
Своих толкований нет: связки только описательные («Сура …», «Хадис», «Слова поддержки», условия акции из ig_content.json).
OFFLINE=1 — тишина вместо чтения и встроенные тексты (для проверки дизайна без сети)."""
import json, math, os, random, subprocess, sys, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageOps
import motion as M
import themes
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kk

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
C = (540, 640)
GAP = 0.5
NAMES = {"ar.husary": "Махмуд Халиль аль-Хусари", "ar.muhammadayyoub": "Мухаммад Айюб", "ar.abdulsamad": "Абдуль-Басит Абдус-Самад"}
if kk.ON:
    NAMES = kk.READERS
L = (lambda k, r: k) if kk.ON else (lambda k, r: r)        # L(казахский, русский)
BEDS = ["forest_stream", "wind_trees", "small_stream", "forest", "summer_rain", "night_rain"]

def dur_of(f):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True)
    return float(p.stdout.strip())

def fetch(url, path):
    for k in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                open(path, "wb").write(r.read()); return
        except Exception as e:
            if k == 2: raise
            print("повтор:", e)

def recitation(nums, reader, work):
    files, durs = [], []
    for n in nums:
        f = os.path.join(work, f"r{n}.mp3")
        if os.environ.get("OFFLINE"):
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "5", f], check=True)
        else:
            br = 64 if reader == "ar.abdulsamad" else 128
            fetch(f"https://cdn.islamic.network/quran/audio/{br}/{reader}/{n}.mp3", f)
        files.append(f); durs.append(dur_of(f))
    return files, durs

def mix(placed, total, out, bed=None, bed_vol=0.0):
    """placed: [(файл, старт_сек)] — чтение; bed — тихий фон природы на всю длину."""
    cmd = ["ffmpeg", "-y", "-v", "error"]; fl = []
    for i, (f, st) in enumerate(placed):
        cmd += ["-i", f]; ms = int(st * 1000)
        fl.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[s{i}]")
    n = len(placed)
    if bed:
        cmd += ["-stream_loop", "-1", "-i", bed]
        fl.append(f"[{n}:a]aresample=44100,aformat=channel_layouts=stereo,atrim=0:{total:.2f},volume={bed_vol},"
                  f"afade=t=in:d=1.5,afade=t=out:st={max(0, total - 2):.2f}:d=2[s{n}]"); n += 1
    fl.append("".join(f"[s{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{total:.2f},loudnorm=I=-15:TP=-1.5[o]")
    subprocess.run(cmd + ["-filter_complex", ";".join(fl), "-map", "[o]", "-c:a", "aac", "-b:a", "192k", out], check=True)

def bed_file(k):
    have = [b for b in BEDS if os.path.exists(os.path.join(ROOT, "sfx", b + ".mp3"))]
    return os.path.join(ROOT, "sfx", have[k % len(have)] + ".mp3") if have else None

def ar_size(s):  return 104 if len(s) <= 28 else 88 if len(s) <= 60 else 72 if len(s) <= 100 else 62
def ru_size(s):
    n = len(s) * (1.2 if kk.ON else 1)          # казахский текст длиннее — шрифт чуть меньше
    return 56 if n <= 60 else 50 if n <= 140 else 44 if n <= 230 else 40

def split_pages(ar, ru, max_ar=110):
    """Длинный аят -> страницы (арабский по словам, перевод — пропорционально), слова не меняются."""
    k = max(1, math.ceil(len(ar) / max_ar), math.ceil(len(ru) / (220 if kk.ON else 260)))
    aw, rw = ar.split(), ru.split()
    pa = [aw[round(i * len(aw) / k):round((i + 1) * len(aw) / k)] for i in range(k)]
    pr = [rw[round(i * len(rw) / k):round((i + 1) * len(rw) / k)] for i in range(k)]
    out = []
    for i in range(k):
        a, r = " ".join(pa[i]), " ".join(pr[i])
        if i < k - 1: r = r.rstrip(",;:—-") + "…"
        if i > 0: r = "…" + r
        out.append((a, r, len(a) / max(1, len(ar))))
    return out

def block_h(text, f, maxw, rtl=False, lh=1.3):
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    n = len((M.wrap_rtl if rtl else M.wrap)(text, f, maxw, tmp))
    return int(f.size * lh * (1.35 if rtl else 1.0)) * n

def intro_kind():
    return M.THEME["intro"] if M.THEME else "converge"

class Scene:
    """Общий фон кадра: свечение, кольца, частицы, ударные волны, узлы-созвездие."""
    def __init__(self, total, n_nodes=0, node_times=(), seed=1, glow=1.0):
        self.orb, self.core, self.node = M.glow_sprite(260, M.GOLD, 2.6), M.glow_sprite(40, (255, 245, 220), 1.4), M.glow_sprite(64, M.GOLD, 2.0)
        self.total, self.items, self.words, self.parts, self.shocks = total, [], [], [], []
        self.n, self.node_t, self.glow = n_nodes, list(node_times), glow
        self.extra = []
    def __call__(self, img, t):
        g = self.glow
        if M.THEME: M.THEME["center"](img, C, t, g)
        else:
            M.paste_alpha(img, self.orb, C, 0.85 * g, 1 + 0.05 * math.sin(t * 2.4))
            M.paste_alpha(img, self.core, C, min(1, 0.4 + g))
        if M.THEME: themes.ornament(M.THEME["orn"], img, C, t * 1.2, M.ease(t / 1.2) * 0.8, M.GOLD)
        else: M.draw_rings(img, C, t * 1.2, M.ease(t / 1.2) * 0.8)
        ang = math.radians(-90 + t * 36)
        M.paste_alpha(img, self.node, (C[0] + 300 * math.cos(ang), C[1] + 300 * math.sin(ang)), 0.8, 0.45)
        for p in self.parts: p.draw(img, t)
        if self.n:
            rot = t * 4
            pts = M.star_points(C, 250, self.n, -90 + rot)
            lay = Image.new("RGBA", (M.W, M.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
            for k, tk in enumerate(self.node_t):
                a = M.ease((t - tk) / 0.6)
                if a <= 0: continue
                M.paste_alpha(img, self.node, pts[k], a, 0.9 + 0.1 * math.sin(t * 3 + k))
                if k > 0:
                    pr = M.ease((t - tk) / 0.9); a0, b0 = pts[k - 1], pts[k]
                    d.line([a0, (a0[0] + (b0[0] - a0[0]) * pr, a0[1] + (b0[1] - a0[1]) * pr)], fill=(*M.GOLD, int(170 * a)), width=2)
                if k == self.n - 1 and self.n > 2:
                    pr = M.ease((t - tk - 0.9) / 0.9); a0, b0 = pts[k], pts[0]
                    if pr > 0: d.line([a0, (a0[0] + (b0[0] - a0[0]) * pr, a0[1] + (b0[1] - a0[1]) * pr)], fill=(*M.GOLD, int(170 * a)), width=2)
                M.shock(img, pts[k], t, tk, r1=170, dur=0.9)
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(3))); img.alpha_composite(lay)
        for f in self.extra: f(img, t)
        for tt in self.shocks: M.shock(img, C, t, tt, r1=420, dur=1.4)
        for it in self.items: it.draw(img, t)
        for w in self.words: w.draw(img, t)

def end_card(sc, e0, total, title, sub, reader=None):
    Tx = M.text_block
    sc.items += [M.Item(Tx(title, M.SERIF(62), M.CREAM, glow=5, maxw=900), 1110, e0, total),
                 M.Item(Tx(sub, M.SANS(26), M.GOLD, spacing=4, maxw=980), 1210, e0 + 0.3, total)]
    if reader:
        sc.items.append(M.Item(Tx(f"{L(kk.READER, 'ЧТЕЦ')}: {NAMES.get(reader, reader).upper()}", M.SANS(24), M.MUTED, spacing=3), 1262, e0 + 0.5, total))
    import ig_render
    logo = ig_render._logo(M.GOLD, 190)
    def lg(img, t):
        a = M.ease((t - e0 - 0.8) / 1.0)
        if a > 0: img.alpha_composite(M.fade(logo, a), ((M.W - logo.width) // 2, 1390))
    sc.extra.append(lg)

# ---------------- аяты под чтение ----------------
def ayahs(out, s, sura_name, a0, ar, ru, nums, reader, repeat=False, kicker=None):
    themes.pick(out)
    work = out.rsplit(".", 1)[0] + "_m"; os.makedirs(work, exist_ok=True)
    files, durs = recitation(nums, reader, work)
    t = 1.4; placed, slots = [], []
    passes = 2 if repeat else 1
    for p in range(passes):
        for i, (f, d) in enumerate(zip(files, durs)):
            placed.append((f, t)); slots.append((p, i, t, t + d)); t += d + GAP
        t += 0.6
    e0 = t; total = t + 4.5
    audio = os.path.join(work, "mix.m4a"); mix(placed, total, audio)
    first = [s_ for s_ in slots if s_[0] == 0]
    sc = Scene(total, n_nodes=min(len(nums), 12) if len(nums) > 1 else 8,
               node_times=[x[2] + 0.1 for x in first][:12] if len(nums) > 1 else [first[0][2] + k * (first[0][3] - first[0][2]) / 8 for k in range(8)])
    Tx = M.text_block
    ref = f"{s}:{a0}" + (f"–{a0 + len(nums) - 1}" if len(nums) > 1 else "")
    sura_t = f"«{sura_name}» сүресі" if kk.ON else f"Сура «{sura_name}»"
    sc.items += [M.Item(Tx(kicker or L(kk.K_LISTEN, "ПОСЛУШАЙ ДО КОНЦА"), M.SANS_B(34), M.GOLD, spacing=7), 1100, 0.0, 1.4 + 0.2, fin=0.3, fout=0.4),
                 M.Item(Tx(sura_t, M.SERIF(96), M.CREAM, glow=6, maxw=980), 1220, 0.15, 1.6, fin=0.35, fout=0.4)]
    sc.parts.append(M.Particles(150, 1, intro_kind(), C, 0.0, 1.6, spread=700))
    sc.parts.append(M.Particles(130, 4, "orbit", C, 1.5, total - 2, spread=330))
    for p, i, st, en in slots:
        sc.shocks.append(st)
        if i % 3 == 0: sc.parts.append(M.Particles(70, 10 + i + p * 50, "burst", C, st, st + 2.2, spread=480))
        nxt = en + GAP - 0.1
        pages = split_pages(ar[i], ru[i])
        tt = st
        for pi, (pa, pr, frac) in enumerate(pages):
            span = (en - st) * frac
            end_p = tt + span - 0.55 if pi < len(pages) - 1 else nxt
            fa, fr = M.AR(ar_size(pa)), M.SERIF(ru_size(pr))
            ha, hr = block_h(pa, fa, 960, rtl=True), block_h(pr, fr, 900)
            top = 1000 + max(0, (620 - ha - hr - 40) // 2)        # блок текста 1000–1620, по центру
            sc.words.append(M.Words(pa, fa, M.CREAM, top + ha / 2, tt, span * 0.85, end_p, maxw=960, rtl=True, glow=6))
            sc.words.append(M.Words(pr, fr, M.MUTED, top + ha + 40 + hr / 2, tt + 0.25, span * 0.85, end_p, maxw=900))
            tt += span
        sc.items.append(M.Item(Tx(f"{L('ҚҰРАН', 'КОРАН')}, {s}:{a0 + i}" + (f" · {L(kk.REPEAT, 'ПОВТОР')}" if p else ""), M.SANS(26), M.GOLD, spacing=4), 1600, st + 0.4, nxt))
    end_card(sc, e0, total, f"{sura_t}, {ref}", L(kk.SOURCE.upper(), "ПЕРЕВОД СМЫСЛОВ Э. КУЛИЕВА"), reader)
    M.render(sc, out, total, audio)
    return total

# ---------------- хадис / слова поддержки без чтения ----------------
def text_piece(out, kicker, intro, body, source, idx=0):
    themes.pick(out)
    work = out.rsplit(".", 1)[0] + "_m"; os.makedirs(work, exist_ok=True)
    nw = len(body.split())
    t_intro = 1.6 if intro else 0.8
    read = nw / 2.6
    t_src = t_intro + 0.6 + read + 0.4
    e0 = t_src + 3.2
    total = e0 + 4.0
    audio = os.path.join(work, "mix.m4a")
    b = bed_file(idx)
    if b: mix([], total, audio, bed=b, bed_vol=0.6)
    else: audio = None
    sc = Scene(total)
    Tx = M.text_block
    sc.parts.append(M.Particles(150, 2, intro_kind(), C, 0.0, 1.8, spread=700))
    sc.parts.append(M.Particles(130, 5, "orbit", C, 1.6, total - 2, spread=330))
    sc.shocks += [0.3, t_intro + 0.6]
    size = 60 if len(body) < 120 else 54 if len(body) < 220 else 48 if len(body) < 320 else 42
    fi, fb = M.SANS(30), M.SERIF(size)
    hi = block_h(intro, fi, 900) if intro else 0
    hb = block_h(body, fb, 900)
    top = 1030
    sc.items.append(M.Item(Tx(kicker, M.SANS_B(34), M.GOLD, spacing=7), 975, 0.2, e0))
    if intro:
        sc.words.append(M.Words(intro, fi, M.MUTED, top + hi / 2, 0.5, 1.0, e0 - 0.2, maxw=900))
    yb = top + hi + (30 if intro else 0)
    sc.words.append(M.Words(body, fb, M.CREAM, yb + hb / 2, t_intro + 0.6, read, e0 - 0.2, maxw=900, glow=3))
    ys = min(1800, yb + hb + 70)
    sc.items.append(M.Item(Tx(source, M.SANS(28), M.GOLD, maxw=900), ys, t_src, e0))
    sc.items.append(M.Item(Tx(L(kk.SAVE, "СОХРАНИТЕ И ОТПРАВЬТЕ БЛИЗКИМ"), M.SANS(24), M.MUTED, spacing=4), min(1860, ys + 80), t_src + 0.8, e0))
    end_card(sc, e0, total, kicker.capitalize() if kicker.isupper() else kicker, L(kk.BRAND, "UMMATI · НАМАЗНЫЕ КОВРИКИ"))
    M.render(sc, out, total, audio)
    return total

# ---------------- продажа коврика ----------------
def sale(out, k=0):
    themes.pick(out)
    work = out.rsplit(".", 1)[0] + "_m"; os.makedirs(work, exist_ok=True)
    cfg = json.load(open(os.path.join(ROOT, "ig_content_kk.json" if kk.ON else "ig_content.json"), encoding="utf-8"))
    off = cfg["offer"]
    promos = [p for p in cfg["promos"] if os.path.exists(os.path.join(ROOT, p[0]))]
    pick = [promos[(k * 3 + i) % len(promos)] for i in range(3)]
    shots = []
    for ph, title, _ in pick:
        im = Image.open(os.path.join(ROOT, ph)).convert("RGB")
        im = ImageOps.fit(im, (860, 1000), Image.LANCZOS)
        im = im.resize((946, 1100), Image.LANCZOS)          # запас под наезд камеры
        mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), 48, fill=255)
        rgba = im.convert("RGBA"); rgba.putalpha(mask)
        shots.append((rgba, title))
    T_SHOT = 3.6
    t_off = 0.4 + 3 * T_SHOT
    total = t_off + 7.5
    audio = os.path.join(work, "mix.m4a")
    b = bed_file(k + 3)
    if b: mix([], total, audio, bed=b, bed_vol=0.6)
    else: audio = None
    sc = Scene(total, glow=0.6)
    Tx = M.text_block
    sc.parts.append(M.Particles(120, 7, "orbit", C, 0.0, total - 1, spread=420))
    def photos(img, t):
        for i, (rgba, title) in enumerate(shots):
            t0 = 0.4 + i * T_SHOT; t1 = t0 + T_SHOT + 0.4
            if t < t0 or t > t1: continue
            a = min(M.ease((t - t0) / 0.6), M.ease((t1 - t) / 0.6))
            z = 0.91 + 0.09 * ((t - t0) / (t1 - t0))
            w, h = int(rgba.width * z), int(rgba.height * z)
            fr = rgba.resize((w, h), Image.BILINEAR)
            img.alpha_composite(M.fade(fr, a), ((M.W - w) // 2, 690 - h // 2))
    sc.extra.append(photos)
    for i, (_, title) in enumerate(shots):
        t0 = 0.4 + i * T_SHOT
        sc.items.append(M.Item(Tx(title, M.SERIF(64), M.CREAM, glow=5, maxw=900), 1390, t0 + 0.4, t0 + T_SHOT + 0.2))
        sc.shocks.append(t0)
    sc.items.append(M.Item(Tx(L(kk.BRAND, "UMMATI · НАМАЗНЫЕ КОВРИКИ"), M.SANS_B(28), M.GOLD, spacing=6), 1520, 0.6, t_off))
    sc.shocks.append(t_off)
    sc.parts.append(M.Particles(110, 9, "burst", C, t_off, t_off + 2.4, spread=560))
    sc.items += [M.Item(Tx(off["kicker"].upper(), M.SANS_B(40), M.GOLD, spacing=8), 1000, t_off + 0.1, total),
                 M.Item(Tx(off["title"], M.SERIF(104), M.CREAM, glow=8, maxw=980), 1130, t_off + 0.4, total),
                 M.Item(Tx(off["body"], M.SERIF(48), M.MUTED, maxw=880), 1290, t_off + 1.0, total),
                 M.Item(Tx(L(kk.WRITE, "ПИШИТЕ В ДИРЕКТ ИЛИ WHATSAPP"), M.SANS_B(30), M.GOLD, spacing=5), 1470, t_off + 1.8, total)]
    import ig_render
    logo = ig_render._logo(M.GOLD, 170)
    def lg(img, t):
        a = M.ease((t - t_off - 2.2) / 1.0)
        if a > 0: img.alpha_composite(M.fade(logo, a), ((M.W - logo.width) // 2, 1580))
    sc.extra.append(lg)
    M.render(sc, out, total, audio)
    return total, pick

# ---------------- ролики с ковриками (ежедневно): коллекция / один цвет / подарочный набор ----------------
WHATSAPP = "+7 707 834 25 25"

def rug_reel(out, shots, kicker, title, lines, k=0, icons=None):
    """shots: [(фото, заголовок, подпись)] — фото с наездом камеры; в конце карточка с призывом и номером WhatsApp.
    icons: [(вид, текст)] — строки комплекта с иконками (вода Зам-Зам, тасбих, упаковка)."""
    themes.pick(out)
    work = out.rsplit(".", 1)[0] + "_m"; os.makedirs(work, exist_ok=True)
    imgs = []
    for ph, t, sub in shots:
        im = Image.open(os.path.join(ROOT, ph)).convert("RGB")
        im = ImageOps.fit(im, (860, 1000), Image.LANCZOS).resize((946, 1100), Image.LANCZOS)
        mask = Image.new("L", im.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, *im.size), 48, fill=255)
        rgba = im.convert("RGBA"); rgba.putalpha(mask); imgs.append(rgba)
    T_SHOT = 3.2
    t_off = 0.4 + len(shots) * T_SHOT
    total = t_off + 7.5
    audio = os.path.join(work, "mix.m4a")
    b = bed_file(k + 3)
    if b: mix([], total, audio, bed=b, bed_vol=0.6)
    else: audio = None
    sc = Scene(total, glow=0.6)
    Tx = M.text_block
    sc.parts.append(M.Particles(120, 7, "orbit", C, 0.0, total - 1, spread=420))
    def photos(img, t):
        for i, rgba in enumerate(imgs):
            t0 = 0.4 + i * T_SHOT; t1 = t0 + T_SHOT + 0.4
            if t < t0 or t > t1: continue
            a = min(M.ease((t - t0) / 0.6), M.ease((t1 - t) / 0.6))
            z = 0.91 + 0.09 * ((t - t0) / (t1 - t0))
            w, h = int(rgba.width * z), int(rgba.height * z)
            img.alpha_composite(M.fade(rgba.resize((w, h), Image.BILINEAR), a), ((M.W - w) // 2, 690 - h // 2))
    sc.extra.append(photos)
    for i, (_, t, sub) in enumerate(shots):
        t0 = 0.4 + i * T_SHOT
        sc.items.append(M.Item(Tx(t, M.SERIF(64), M.CREAM, glow=5, maxw=900), 1360, t0 + 0.4, t0 + T_SHOT + 0.2))
        if sub: sc.items.append(M.Item(Tx(sub, M.SANS(30), M.MUTED, maxw=880), 1450, t0 + 0.7, t0 + T_SHOT + 0.2))
        sc.shocks.append(t0)
    sc.items.append(M.Item(Tx(L(kk.BRAND, "UMMATI · НАМАЗНЫЕ КОВРИКИ"), M.SANS_B(28), M.GOLD, spacing=6), 1560, 0.6, t_off))
    sc.shocks.append(t_off)
    sc.parts.append(M.Particles(110, 9, "burst", C, t_off, t_off + 2.4, spread=560))
    sc.items += [M.Item(Tx(kicker.upper(), M.SANS_B(40), M.GOLD, spacing=8), 960, t_off + 0.1, total),
                 M.Item(Tx(title, M.SERIF(96), M.CREAM, glow=8, maxw=960), 1080, t_off + 0.4, total)]
    y = 1200
    if icons:
        for j, (kind, txt) in enumerate(icons):
            ic = _icon(kind, 64)
            row = Image.new("RGBA", (M.W, 90), (0, 0, 0, 0)); ImageDraw.Draw(row)
            f = M.SANS(36); tw = ImageDraw.Draw(row).textlength(txt, font=f); x0 = int((M.W - tw - 84) / 2)
            row.alpha_composite(ic, (x0, 13)); ImageDraw.Draw(row).text((x0 + 84, 45), txt, font=f, fill=M.CREAM, anchor="lm")
            sc.items.append(M.Item(row, y + j * 82, t_off + 0.9 + j * 0.25, total, rise=16))
        y += len(icons) * 82 + 20
    for j, ln in enumerate(lines):
        sc.items.append(M.Item(Tx(ln, M.SERIF(46), M.MUTED, maxw=900), y + j * 64, t_off + 1.0 + j * 0.2, total))
    y += len(lines) * 64 + 40
    sc.items += [M.Item(Tx(L(kk.WRITE, "ПИШИТЕ В ДИРЕКТ ИЛИ WHATSAPP"), M.SANS_B(30), M.GOLD, spacing=5), y, t_off + 1.8, total),
                 M.Item(Tx(WHATSAPP, M.SANS_B(44), M.CREAM, spacing=2), y + 70, t_off + 2.1, total)]
    import ig_render
    logo = ig_render._logo(M.GOLD, 150)
    def lg(img, t):
        a = M.ease((t - t_off - 2.4) / 1.0)
        if a > 0: img.alpha_composite(M.fade(logo, a), ((M.W - logo.width) // 2, min(1720, int(y + 150))))
    sc.extra.append(lg)
    M.render(sc, out, total, audio)
    return total

def _icon(kind, sz):
    im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0)); d = ImageDraw.Draw(im); s = sz; col = (*M.GOLD, 255); wd = max(3, sz // 22)
    if kind == "bottle":
        d.rounded_rectangle((s*.38, s*.06, s*.62, s*.18), 4, outline=col, width=wd); d.rounded_rectangle((s*.28, s*.22, s*.72, s*.94), 10, outline=col, width=wd)
    elif kind == "tasbih":
        cx, cy, r = s/2, s*.4, s*.3
        for q in range(16):
            a = math.radians(-55 + q*290/15); x, y = cx + r*math.cos(a), cy + r*math.sin(a); d.ellipse((x-4, y-4, x+4, y+4), fill=col)
        d.line((cx, cy+r, cx, s*.9), fill=col, width=wd)
    else:
        d.rectangle((s*.14, s*.36, s*.86, s*.5), outline=col, width=wd); d.rectangle((s*.2, s*.5, s*.8, s*.92), outline=col, width=wd)
        d.line((s*.5, s*.36, s*.5, s*.92), fill=col, width=wd)
        d.ellipse((s*.26, s*.12, s*.5, s*.36), outline=col, width=wd); d.ellipse((s*.5, s*.12, s*.74, s*.36), outline=col, width=wd)
    return im
