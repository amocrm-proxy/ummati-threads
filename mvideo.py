"""Моушн-версии роликов (папка motion/): аяты под чтение, хадис, слова поддержки, продажа коврика + готовые спецвыпуски.
Вызывается из video.py; при ошибке video.py откатывается на старые шаблоны. Тексты — дословно, своих толкований нет."""
import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "motion"))
import kk
OFFER = "Ummati — намазные коврики. Instagram: @ummati.family"

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
    total = auto.ayahs(out, s, kk.NAMES[s - 1] if kk.ON else name, a, ar, ru, nums, reader)
    whole = a == 1 and a + len(ar) - 1 == V.COUNTS[s - 1]
    if kk.ON:
        part = "" if whole else (f", {a}-аят" if len(ar) == 1 else f", {a}–{a + len(ar) - 1} аяттар")
        _meta(out, f"{kk.sura(s)}{part} — оқылуы мен мағынасы #shorts", "#құран #сүре #аят #ислам #намаз #quran")
        return total
    part = "" if whole else (f", аят {a}" if len(ar) == 1 else f", аяты {a}–{a + len(ar) - 1}")
    ref = f"{s}" if whole else f"{s}:{a}" + (f"-{a + len(ar) - 1}" if len(ar) > 1 else "")
    _meta(out, f"Сура «{name}»{part} — чтение и перевод смыслов #shorts",
          " ".join(ru) + f"\n\nКоран, {ref}. Перевод смыслов: Э. Кулиев. Чтец: {auto.NAMES[reader]}.\n\n" + _smysl(s, a) +
          OFFER + "\n\n#коран #ислам #сура #аят #намаз #quran #shorts")
    return total

def ayah_single(out, s, a, kicker=None, title=None, tags="#коран #ислам #аят #намаз #quran #shorts"):
    import video as V, auto
    _, _, _, ar, ru, nums = V.load(f"{s}:{a}")
    name = V.NAMES[s - 1]
    reader = "ar.muhammadayyoub"
    total = auto.ayahs(out, s, kk.NAMES[s - 1] if kk.ON else name, a, ar, ru, nums, reader, repeat=True, kicker=kicker)
    text = ru[0]
    if kk.ON:
        short = text if len(text) <= 70 else text[:text.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
        _meta(out, title or f"«{short}» — {kk.ref(s, a)} #shorts", tags if "#құран" in tags else "#құран #аят #ислам #намаз #quran")
        return total
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
    return hadith_any(out, h, "ХАДИС", "#хадис #сунна #ислам #пророк #мусульмане #shorts")

def hadith_any(out, h, kicker, tags):
    """Светлый/тёмный фон чередуются по слотам (themes.is_light); светлый — стиль «Рукопись»."""
    import themes
    if themes.is_light(out):
        try:
            return hadith_light(out, h, kicker, tags)
        except Exception as e:                   # светлый стиль не собрался — тёмный моушн как раньше
            print("Рукопись не собралась:", e)
    return hadith_piece(out, h, kicker, tags)

def hadith_light(out, h, kicker="ХАДИС", tags="#хадис #сунна #ислам #пророк #мусульмане #shorts"):
    """Светлый стиль «Рукопись» + обложка для Reels (<имя>_cover.jpg). Без номеров выпусков."""
    import content as C, auto, light
    intro, body = C.hadith_parts(h)
    shown = f"«{body}»" if intro else body
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    grade = h.get("grade") or "Хадис"
    total = light.hadith(out, kicker, intro, shown, f"{attr} · {grade}", bed=auto.bed_file(int(h["id"]) % 7))
    head = body if len(body) <= 48 else body[:body.rfind(" ", 0, 44)].rstrip(",;:—-") + "…"
    try:
        light.cover(out.rsplit(".", 1)[0] + "_cover.jpg", kicker, f"«{head}»" if intro else head, sub=attr.upper()[:40])
    except Exception as e:
        print("обложка:", e)
    q = re.findall(r"[«“]([^«»“”]{15,})[»”]", body)
    core = (q[-1] if q else body).strip().strip('"“”«» ')
    short = core if len(core) <= 70 else core[:core.rfind(" ", 0, 66)].rstrip(",;:—-") + "…"
    _meta(out, f"«{short}» — хадис #shorts" if (q or intro) else f"{short} — хадис #shorts",
          tags)
    return total

def support(out):
    import support as S
    st = _state("support_state.json", {"i": 0}); k = int(st.get("i", 0))
    for j in range(k, k + 10):
        x = S.item(j)
        if not x:
            continue
        if x[0] == "ayah" and len(x[3]) <= 300:
            total = ayah_single(out, x[1], x[2], kicker=S.KICKER,
                                tags="#құран #демеу #ислам" if kk.ON else "#коран #поддержка #ислам #shorts"); break
        if x[0] == "hadith" and sum(map(len, S.C.hadith_parts(x[1]))) <= 420:
            total = hadith_any(out, x[1], S.KICKER, "#хадис #поддержка #ислам #shorts"); break
    else:
        raise SystemExit("Нет подходящего текста для «Слов поддержки»")
    _save("support_state.json", {"i": j + 1})
    return total

RUG_TAGS = "#намазныйковрик #жайнамаз #ummati #подарок #казахстан #намаз #shorts"
IN_SET = ["Микровелюр с мягким ворсом · не скользит", "В комплекте: вода Зам-Зам, чётки из агата", "и подарочная упаковка"]
COLORS = [
    ("Изумрудный", [("green_arch.jpg", "Изумрудный", "Коврик в форме арки"), ("L1033132.jpg", "С золотой кисточкой", ""),
                    ("green_label.jpg", "Мягкий ворс и нашивка Ummati", ""), ("green_tex.jpg", "Рельефный узор", "")]),
    ("Шоколадный", [("brown_arch.jpg", "Шоколадный", "Тёплый и уютный"), ("L1033112.jpg", "Мягкий бархатистый ворс", ""),
                    ("brown_tex.jpg", "Рельефный узор", "")]),
    ("Графит", [("grey_arch.jpg", "Графит", "Спокойный и современный"), ("L1033127.jpg", "Мягкий ворс бережёт колени", ""),
                ("grey_label.jpg", "Аккуратный кант и нашивка", ""), ("L1033130.jpg", "Рельефный узор", "")]),
    ("Чёрный", [("black_arch.jpg", "Чёрный", "Строгая классика"), ("L1033115.jpg", "Глубокий чёрный", ""),
                ("L1033117.jpg", "Фирменная нашивка Ummati", "")]),
]
GIFT = [("gift_set.jpg", "Готовый подарок", "Фирменный пакет, вода Зам-Зам и чётки из агата"), ("stack.jpg", "Четыре цвета на выбор", ""),
        ("L1033132.jpg", "Подарок, которым пользуются 5 раз в день", "")]

if kk.ON:                                        # казахский режим — те же фото, тексты на казахском
    RUG_TAGS = "#жайнамаз #намазныйковрик #ummati #сыйлық #қазақстан #намаз"
    IN_SET = ["Микровелюр, жұмсақ түгі бар · тайғанамайды", "Жиынтықта: Зәмзәм суы, агат тасбих", "және сыйлық қаптамасы"]
    COLORS = [
        ("Зүмірет", [("green_arch.jpg", "Зүмірет түсті", "Арка пішінді жайнамаз"), ("L1033132.jpg", "Алтын түсті шашағымен", ""),
                     ("green_label.jpg", "Жұмсақ түгі және Ummati белгісі", ""), ("green_tex.jpg", "Бедерлі өрнек", "")]),
        ("Шоколад", [("brown_arch.jpg", "Шоколад түсті", "Жылы әрі жайлы"), ("L1033112.jpg", "Жұмсақ барқыт түгі", ""),
                     ("brown_tex.jpg", "Бедерлі өрнек", "")]),
        ("Графит", [("grey_arch.jpg", "Графит түсті", "Байсалды әрі заманауи"), ("L1033127.jpg", "Жұмсақ түгі тізені аялайды", ""),
                    ("grey_label.jpg", "Ұқыпты жиегі мен белгісі", ""), ("L1033130.jpg", "Бедерлі өрнек", "")]),
        ("Қара", [("black_arch.jpg", "Қара түсті", "Талғампаз классика"), ("L1033115.jpg", "Терең қара түс", ""),
                  ("L1033117.jpg", "Ummati фирмалық белгісі", "")]),
    ]
    GIFT = [("gift_set.jpg", "Дайын сыйлық", "Фирмалық пакет, Зәмзәм суы және агат тасбих"), ("stack.jpg", "Таңдауға төрт түс", ""),
            ("L1033132.jpg", "Күніне бес рет қолданылатын сыйлық", "")]

def sale(out):
    """Ролик с ковриками (ежедневно): по очереди коллекция → один цвет → подарочный набор."""
    import auto
    st = _state("sale_state.json", {"i": 0}); k = int(st.get("i", 0))
    fmt = k % 3
    have = lambda shots: [x for x in shots if os.path.exists(os.path.join(HERE, x[0]))]
    if fmt == 1:
        name, shots = COLORS[(k // 3) % len(COLORS)]
        total = auto.rug_reel(out, have(shots), name, "Жайнамаз" if kk.ON else "Коврик для намаза", IN_SET, k=k)
        title = f"{name} түсті жайнамаз — Ummati #shorts" if kk.ON else f"{name} коврик для намаза — Ummati #shorts"
    elif fmt == 2 and os.path.exists(os.path.join(HERE, "gift_set.jpg")):
        if kk.ON:
            total = auto.rug_reel(out, have(GIFT), "Ummati", "Дайын сыйлық", [], k=k,
                                  icons=[("bottle", "Зәмзәм суы"), ("tasbih", "Агат тасбих"), ("gift", "Сыйлық қаптамасы")])
            title = "Дайын сыйлық: жайнамаз, Зәмзәм суы және тасбих — Ummati #shorts"
        else:
            total = auto.rug_reel(out, have(GIFT), "Ummati", "Готовый подарок", [], k=k,
                                  icons=[("bottle", "Вода Зам-Зам"), ("tasbih", "Чётки из агата"), ("gift", "Подарочная упаковка")])
            title = "Готовый подарок: коврик для намаза, Зам-Зам и чётки — Ummati #shorts"
    else:
        cfg = json.load(open(os.path.join(HERE, "ig_content_kk.json" if kk.ON else "ig_content.json"), encoding="utf-8"))
        promos = [p for p in cfg["promos"] if os.path.exists(os.path.join(HERE, p[0]))]
        pick = [promos[(k + i * 5) % len(promos)] for i in range(3)]
        total = auto.rug_reel(out, [(p[0], p[1], p[2]) for p in pick], "Ummati", "Жайнамаздар" if kk.ON else "Коврики для намаза", IN_SET, k=k)
        title = ("Ummati жайнамаздары — күніне бес рет қолданылатын сыйлық #shorts" if kk.ON else
                 "Коврики для намаза Ummati — подарок, которым пользуются 5 раз в день #shorts")
    _save("sale_state.json", {"i": k + 1})
    _meta(out, title, RUG_TAGS)
    return total

def build(spec, out):
    import render as R, video as V
    R.ensure_fonts(); V.ensure_ar_font()
    kind = spec.split(":")[0]
    if kk.ON and kind == "hadith":               # казахский режим: хадисов нет — вместо них «Сильный аят»
        kind = "card"
    return {"auto": lambda: ayah_passage(spec, out), "card": lambda: strong_ayah(out), "hadith": lambda: hadith(out),
            "support": lambda: support(out), "sale": lambda: sale(out)}[kind]()
