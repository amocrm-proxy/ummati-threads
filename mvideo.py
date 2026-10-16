"""Моушн-версии роликов (папка motion/): аяты под чтение, хадис, слова поддержки, продажа коврика + готовые спецвыпуски.
Вызывается из video.py; при ошибке video.py откатывается на старые шаблоны. Тексты — дословно, своих толкований нет."""
import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "motion"))
OFFER = ("Ummati — намазные коврики. Акция 1+1: 2 коврика за 9 900 ₸, вода Зам-Зам, тасбих и подарочная упаковка в комплекте. "
         "Instagram: @ummati.family")

def _state(name, default):
    p = os.path.join(HERE, name)
    return json.load(open(p)) if os.path.exists(p) else default

def _save(name, data):
    json.dump(data, open(os.path.join(HERE, name), "w"), ensure_ascii=False)

def _meta(out, title, desc):
    json.dump({"title": title, "description": desc}, open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def special(out):
    """Готовый спецвыпуск из videos/motion/ (сделан вручную по теме), который ещё не публиковался."""
    st = _state("specials_state.json", {"done": []})
    for f in sorted(glob.glob(os.path.join(HERE, "videos", "motion", "*.mp4"))):
        name = os.path.basename(f)
        j = f.rsplit(".", 1)[0] + ".json"
        if name in st["done"] or not os.path.exists(j):
            continue
        shutil.copy(f, out); shutil.copy(j, out.rsplit(".", 1)[0] + ".json")
        st["done"].append(name); _save("specials_state.json", st)
        print("Спецвыпуск:", name)
        return True
    return False

def _smysl(s, a):
    try:
        import content
        t = content.tafsir(s, a)
        return f"Смысл: {t[0]}\n({t[1]}, перевод Э. Кулиева, сокращено)\n\n" if t else ""
    except Exception as e:
        print("тафсир:", e); return ""

def ayah_passage(spec, out):
    import video as V, auto
    if special(out):
        return 0.0
    reader = "ar.abdulsamad" if spec[16:18] == "18" else "ar.husary"
    sp, _ = V.auto_spec(spec[5:] or None)
    s, _, a, ar, ru, nums = V.load(sp)
    name = V.NAMES[s - 1]
    total = auto.ayahs(out, s, name, a, ar, ru, nums, reader)
    whole = a == 1 and a + len(ar) - 1 == V.COUNTS[s - 1]
    part = "" if whole else (f", аят {a}" if len(ar) == 1 else f", аяты {a}–{a + len(ar) - 1}")
    ref = f"{s}" if whole else f"{s}:{a}" + (f"-{a + len(ar) - 1}" if len(ar) > 1 else "")
    _meta(out, f"Сура «{name}»{part} — чтение и перевод смыслов #shorts",
          " ".join(ru) + f"\n\nКоран, {ref}. Перевод смыслов: Э. Кулиев. Чтец: {auto.NAMES[reader]}.\n\n" + _smysl(s, a) +
          OFFER + "\n\n#коран #ислам #намаз #сура #shorts")
    return total

def ayah_single(out, s, a, kicker=None, title=None, tags="#коран #ислам #аят #shorts"):
    import video as V, auto
    _, _, _, ar, ru, nums = V.load(f"{s}:{a}")
    name = V.NAMES[s - 1]
    reader = "ar.muhammadayyoub"
    total = auto.ayahs(out, s, name, a, ar, ru, nums, reader, repeat=True, kicker=kicker)
    text = ru[0]
    short = text if len(text) <= 70 else text[:text.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
    _meta(out, title or f"«{short}» — Коран {s}:{a} #shorts",
          f"«{text}»\n\nКоран, сура «{name}», аят {a}. Перевод смыслов: Э. Кулиев. Чтец: {auto.NAMES[reader]}.\n\n" + _smysl(s, a) +
          OFFER + f"\n\n{tags}")
    return total

def strong_ayah(out):
    import card
    if special(out):
        return 0.0
    ref, text, num, s, a, idx = card.pick()
    return ayah_single(out, s, a)

def hadith_piece(out, h, kicker, tags):
    import content as C, auto
    intro, body = C.hadith_parts(h)
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    total = auto.text_piece(out, kicker, intro, body, f"{attr} · {h.get('grade') or 'Хадис'}", idx=int(h["id"]) % 7)
    q = re.findall(r"[«“]([^«»“”]{15,})[»”]", body)
    core = q[-1].strip() if q else body
    short = core if len(core) <= 70 else core[:core.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
    short = f"«{short}»" if q else short
    _meta(out, f"{short} — хадис #shorts",
          (intro + "\n" if intro else "") + body + f"\n\n{attr}. {h.get('grade') or 'Хадис'}.\n"
          "Перевод: Энциклопедия переведённых пророческих хадисов (HadeethEnc.com).\n\n" + OFFER + f"\n\n{tags}")
    return total

def hadith(out):
    import hadith_video
    h, _ = hadith_video.pick()
    return hadith_piece(out, h, "ХАДИС", "#хадис #сунна #ислам #пророк #shorts")

def support(out):
    import support as S
    st = _state("support_state.json", {"i": 0}); k = int(st.get("i", 0))
    for j in range(k, k + 10):
        x = S.item(j)
        if not x:
            continue
        if x[0] == "ayah" and len(x[3]) <= 300:
            total = ayah_single(out, x[1], x[2], kicker=S.KICKER, tags="#коран #поддержка #ислам #shorts"); break
        if x[0] == "hadith" and sum(map(len, S.C.hadith_parts(x[1]))) <= 420:
            total = hadith_piece(out, x[1], S.KICKER, "#хадис #поддержка #ислам #shorts"); break
    else:
        raise SystemExit("Нет подходящего текста для «Слов поддержки»")
    _save("support_state.json", {"i": j + 1})
    return total

def sale(out):
    import auto
    st = _state("sale_state.json", {"i": 0}); k = int(st.get("i", 0))
    total, pick = auto.sale(out, k)
    _save("sale_state.json", {"i": k + 1})
    off = json.load(open(os.path.join(HERE, "ig_content.json"), encoding="utf-8"))["offer"]
    _meta(out, f"{off['kicker']}: {off['title']} — намазные коврики Ummati #shorts",
          f"{off['kicker']}: {off['title']}. {off['body']}.\n\n" + " · ".join(p[1] for p in pick) +
          "\n\nЗаказ: пишите в директ Instagram @ummati.family или в WhatsApp.\n\n#намаз #жайнамаз #намазныйковрик #ummati #подарок #казахстан #shorts")
    return total

def build(spec, out):
    import render as R, video as V
    R.ensure_fonts(); V.ensure_ar_font()
    kind = spec.split(":")[0]
    return {"auto": lambda: ayah_passage(spec, out), "card": lambda: strong_ayah(out), "hadith": lambda: hadith(out),
            "support": lambda: support(out), "sale": lambda: sale(out)}[kind]()
