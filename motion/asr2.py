"""Моушн-ролик v2: сура 103 «Аль-Аср» под чтение. Анимация привязана к длительности каждого аята в аудио.
Часть 1 — басмала + аяты 1–3 (сюжет). Часть 2 — повтор чтения суры с «созвездием» четырёх качеств (дольше слушают Коран).
Тексты — дословно (quran-uthmani + ru.kuliev). Запуск: python asr2.py out.mp4 [ar.husary]   (OFFLINE=1 — тишина для проверки)"""
import json, math, os, subprocess, sys, urllib.request
from PIL import Image, ImageDraw, ImageFilter
import motion as M

AR = ["وَٱلْعَصْرِ", "إِنَّ ٱلْإِنسَٰنَ لَفِى خُسْرٍ",
      "إِلَّا ٱلَّذِينَ ءَامَنُوا۟ وَعَمِلُوا۟ ٱلصَّٰلِحَٰتِ وَتَوَاصَوْا۟ بِٱلْحَقِّ وَتَوَاصَوْا۟ بِٱلصَّبْرِ"]
RU = ["Клянусь предвечерним временем (или временем)!", "Воистину, каждый человек в убытке,",
      "кроме тех, которые уверовали, совершали праведные деяния, заповедали друг другу истину и заповедали друг другу терпение!"]
FOUR = ["уверовали", "совершали праведные деяния", "заповедали друг другу истину", "заповедали друг другу терпение"]
NUMS = [1, 6177, 6178, 6179]            # басмала (1:1) + 103:1–3
NAMES = {"ar.husary": "Махмуд Халиль аль-Хусари", "ar.muhammadayyoub": "Мухаммад Айюб", "ar.abdulsamad": "Абдуль-Басит Абдус-Самад"}
C = (540, 640)
GAP = 0.45

def phrase_fracs():
    s = AR[2]; keys = ["ءَامَنُوا۟", "وَعَمِلُوا۟", "وَتَوَاصَوْا۟ بِٱلْحَقِّ", "وَتَوَاصَوْا۟ بِٱلصَّبْرِ"]
    out, pos = [], 0
    for k in keys:
        i = s.find(k, pos); out.append(i / len(s)); pos = i + 1
    return out

def get_audio(reader, work):
    files, durs = [], []
    for n in NUMS:
        f = os.path.join(work, f"a{n}.mp3")
        if os.environ.get("OFFLINE"):
            d = {1: 6.0, 6177: 3.2, 6178: 4.6, 6179: 13.5}[n]
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", str(d), f], check=True)
        else:
            br = 64 if reader == "ar.abdulsamad" else 128
            with urllib.request.urlopen(f"https://cdn.islamic.network/quran/audio/{br}/{reader}/{n}.mp3", timeout=60) as r:
                open(f, "wb").write(r.read())
        p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], capture_output=True, text=True)
        files.append(f); durs.append(float(p.stdout.strip()))
    return files, durs

def timeline(durs):
    b, a1, a2, a3 = durs
    t = 0.3; T = {}
    T["b"] = (t, t + b); t += b + GAP
    for k, a in zip(("a1", "a2", "a3"), (a1, a2, a3)):
        T[k] = (t, t + a); t += a + GAP
    t += 0.6
    for k, a in zip(("r1", "r2", "r3"), (a1, a2, a3)):
        T[k] = (t, t + a); t += a + 0.3
    T["end"] = (t, t + 4.0)
    return T, t + 4.0

def mix(files, T, total, out):
    order = [("b", 0), ("a1", 1), ("a2", 2), ("a3", 3), ("r1", 1), ("r2", 2), ("r3", 3)]
    cmd = ["ffmpeg", "-y", "-v", "error"]; fl = []
    for i, (k, fi) in enumerate(order):
        cmd += ["-i", files[fi]]
        ms = int(T[k][0] * 1000)
        fl.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[s{i}]")
    fl.append("".join(f"[s{i}]" for i in range(len(order))) + f"amix=inputs={len(order)}:normalize=0,apad,atrim=0:{total:.2f},loudnorm=I=-15:TP=-1.5[o]")
    subprocess.run(cmd + ["-filter_complex", ";".join(fl), "-map", "[o]", "-c:a", "aac", "-b:a", "192k", out], check=True)

def build(out, reader="ar.husary"):
    work = out.rsplit(".", 1)[0] + "_motion"; os.makedirs(work, exist_ok=True)
    files, durs = get_audio(reader, work)
    T, total = timeline(durs)
    audio = os.path.join(work, "mix.m4a"); mix(files, T, total, audio)
    fr = phrase_fracs()
    orb, core, node = M.glow_sprite(260, M.GOLD, 2.6), M.glow_sprite(40, (255, 245, 220), 1.4), M.glow_sprite(70, M.GOLD, 2.0)
    Tx = M.text_block
    pts4 = M.star_points(C, 250, 4, -90); pts8 = M.star_points(C, 250, 8, -90)
    node_t = [T["a3"][0] + f * (T["a3"][1] - T["a3"][0]) + 0.2 for f in fr]

    b0, b1 = T["b"]
    items = [
        M.Item(Tx("ЕСТЬ ЛИ В ТЕБЕ", M.SANS_B(40), M.GOLD, spacing=8), 1080, 0.0, b1, fin=0.35),
        M.Item(Tx("эти 4 качества?", M.SERIF(110), M.CREAM, glow=7), 1210, 0.25, b1, fin=0.45),
        M.Item(Tx("Сура «Аль-Аср» · 103", M.SANS(30), M.MUTED, spacing=3), 1360, 1.2, b1),
    ]
    words = []
    for k, i in (("a1", 0), ("a2", 1), ("a3", 2)):
        s, e = T[k]; nxt = e + GAP - 0.1
        size = 108 if i == 0 else 92 if i == 1 else 68
        words.append(M.Words(AR[i], M.AR(size), M.CREAM, 1110 if i < 2 else 1090, s, (e - s) * 0.85, nxt, maxw=940, rtl=True, glow=6))
        words.append(M.Words(RU[i], M.SERIF(54 if i < 2 else 46), M.MUTED, 1300 if i < 2 else 1370, s + 0.3, (e - s) * 0.85, nxt, maxw=880))
        items.append(M.Item(Tx(f"КОРАН, 103:{i + 1}", M.SANS(26), M.GOLD, spacing=4), 1440 if i < 2 else 1560, s + 0.5, nxt))
    # часть 2 — повтор чтения: созвездие + список
    r0, r_end = T["r1"][0], T["r3"][1]
    items.append(M.Item(Tx("ЧЕТЫРЕ КАЧЕСТВА ИЗ АЯТА 3", M.SANS_B(30), M.GOLD, spacing=6), 1050, r0, r_end + 0.3))
    for k in range(4):
        items.append(M.Item(Tx(f"{k + 1}   {FOUR[k]}", M.SERIF(54), M.CREAM, maxw=900), 1150 + k * 92, r0 + 0.6 + k * 0.5, r_end + 0.3, rise=20))
    items.append(M.Item(Tx("СЛУШАЙТЕ И ПЕРЕЧИТЫВАЙТЕ — СОХРАНИТЕ", M.SANS(26), M.MUTED, spacing=4), 1560, T["r2"][0], r_end + 0.3))
    e0 = T["end"][0]
    items += [M.Item(Tx("Сура «Аль-Аср», 103:1–3", M.SERIF(62), M.CREAM, glow=5), 1110, e0, total),
              M.Item(Tx("ПЕРЕВОД СМЫСЛОВ Э. КУЛИЕВА", M.SANS(26), M.GOLD, spacing=4), 1205, e0 + 0.3, total),
              M.Item(Tx(f"ЧТЕЦ: {NAMES.get(reader, reader).upper()}", M.SANS(24), M.MUTED, spacing=3), 1255, e0 + 0.5, total)]
    parts = [M.Particles(160, 1, "converge", C, 0.0, b1 * 0.6, spread=700),
             M.Particles(90, 2, "burst", C, T["a1"][0], T["a1"][0] + 2.5, spread=520),
             M.Particles(120, 3, "sink", C, T["a2"][0], T["a2"][1] + 1.5, color=(200, 170, 130), spread=260),
             M.Particles(140, 4, "orbit", C, T["a3"][0], total - 2, spread=330)]
    import ig_render
    logo = ig_render._logo(M.GOLD, 190)

    def glow_level(t):
        if t < T["a2"][0]: return 1.0
        if t < T["a3"][0]: return 1.0 - 0.65 * M.ease((t - T["a2"][0]) / 2.5)
        if t < node_t[0]: return 0.35
        return min(1.0, 0.35 + 0.65 * M.ease((t - node_t[0]) / (node_t[3] - node_t[0] + 1.5)))

    def scene(img, t):
        g = glow_level(t)
        M.paste_alpha(img, orb, C, 0.9 * g, 1 + 0.05 * math.sin(t * 2.4))
        M.paste_alpha(img, core, C, min(1, 0.4 + g))
        M.draw_rings(img, C, t * (1.6 if t < T["a2"][0] else 0.7), M.ease(t / 1.2) * (0.5 + 0.5 * g) * (1 if t < T["r1"][0] else 0.4))
        if t < T["a3"][0]:                                      # «стрелка времени»
            ang = math.radians(-90 + t * 42)
            M.paste_alpha(img, node, (C[0] + 300 * math.cos(ang), C[1] + 300 * math.sin(ang)), 0.9, 0.5)
        for p in parts: p.draw(img, t)
        rot = 0 if t < T["r1"][0] else (t - T["r1"][0]) * 8   # в части 2 созвездие медленно вращается
        p4 = M.star_points(C, 250, 4, -90 + rot); p8 = M.star_points(C, 250, 8, -90 + rot)
        lay = Image.new("RGBA", (M.W, M.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        endfade = 1 if t < e0 else max(0, 1 - (t - e0) / 1.2)
        for k, tk in enumerate(node_t):
            a = M.ease((t - tk) / 0.6) * endfade
            if a > 0:
                M.paste_alpha(img, node, p4[k], a, 0.95 + 0.12 * math.sin(t * 3 + k))
                pr = M.ease((t - tk) / 0.9)
                d.line([C, (C[0] + (p4[k][0] - C[0]) * pr, C[1] + (p4[k][1] - C[1]) * pr)], fill=(*M.GOLD, int(130 * a)), width=2)
            M.shock(img, p4[k], t, tk, r1=200, dur=1.0)
        s = M.ease((t - (T["a3"][1] - 0.5)) / 2.2) * endfade
        if s > 0:
            for poly in ([p8[i] for i in (0, 2, 4, 6, 0)], [p8[i] for i in (1, 3, 5, 7, 1)]):
                done = s * 4
                for i in range(4):
                    f = min(1, max(0, done - i))
                    if f <= 0: break
                    a0, b0 = poly[i], poly[i + 1]
                    d.line([a0, (a0[0] + (b0[0] - a0[0]) * f, a0[1] + (b0[1] - a0[1]) * f)], fill=(*M.GOLD, 220), width=3)
        if t > T["a3"][0]:
            img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(4))); img.alpha_composite(lay)
        for tt in (T["a1"][0], T["a3"][0], T["r1"][0]):
            M.shock(img, C, t, tt, r1=420, dur=1.4)
        for it in items: it.draw(img, t)
        for w in words: w.draw(img, t)
        la = M.ease((t - e0 - 0.8) / 1.0)
        if la > 0:
            img.alpha_composite(M.fade(logo, la), ((M.W - logo.width) // 2, 1380))

    M.render(scene, out, total, audio)
    meta = {"title": "Есть ли в тебе эти 4 качества? Сура «Аль-Аср» #shorts",
            "description": " ".join(RU) + f"\n\nКоран, сура 103 «Аль-Аср». Перевод смыслов: Э. Кулиев. Чтец: {NAMES.get(reader, reader)}.\n\n"
                           "Ummati — намазные коврики. Instagram: @ummati.family\n\n#коран #ислам #сура #shorts"}
    json.dump(meta, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return total

if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import render as R, video as V                      # шрифты (Montserrat, Cormorant, Amiri Quran)
    R.ensure_fonts(); V.ensure_ar_font()
    print("Готово:", build(sys.argv[1] if len(sys.argv) > 1 else "asr2.mp4", sys.argv[2] if len(sys.argv) > 2 else "ar.husary"))
