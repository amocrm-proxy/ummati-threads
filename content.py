"""Общий контент ummati: аяты по порядку (весь Коран, перевод Э. Кулиева) и хадисы (hadiths.json).
Ни одного слова от себя: аят — только перевод Кулиева, хадис — только текст, источник и степень достоверности."""
import json, re, time, urllib.request
import kk

TOTAL_AYAHS = 6236
NAMES = ["Аль-Фатиха", "Аль-Бакара", "Али Имран", "Ан-Ниса", "Аль-Маида", "Аль-Анам", "Аль-Араф", "Аль-Анфаль", "Ат-Тауба", "Юнус", "Худ", "Юсуф", "Ар-Раад", "Ибрахим", "Аль-Хиджр", "Ан-Нахль", "Аль-Исра", "Аль-Кахф", "Марьям", "Та Ха", "Аль-Анбия", "Аль-Хадж", "Аль-Муминун", "Ан-Нур", "Аль-Фуркан", "Аш-Шуара", "Ан-Намль", "Аль-Касас", "Аль-Анкабут", "Ар-Рум", "Лукман", "Ас-Саджда", "Аль-Ахзаб", "Саба", "Фатыр", "Ясин", "Ас-Саффат", "Сад", "Аз-Зумар", "Гафир", "Фуссылят", "Аш-Шура", "Аз-Зухруф", "Ад-Духан", "Аль-Джасия", "Аль-Ахкаф", "Мухаммад", "Аль-Фатх", "Аль-Худжурат", "Каф", "Аз-Зарият", "Ат-Тур", "Ан-Наджм", "Аль-Камар", "Ар-Рахман", "Аль-Вакиа", "Аль-Хадид", "Аль-Муджадаля", "Аль-Хашр", "Аль-Мумтахана", "Ас-Сафф", "Аль-Джумуа", "Аль-Мунафикун", "Ат-Тагабун", "Ат-Талак", "Ат-Тахрим", "Аль-Мульк", "Аль-Калям", "Аль-Хакка", "Аль-Мааридж", "Нух", "Аль-Джинн", "Аль-Муззаммиль", "Аль-Муддассир", "Аль-Кияма", "Аль-Инсан", "Аль-Мурсалят", "Ан-Наба", "Ан-Назиат", "Абаса", "Ат-Таквир", "Аль-Инфитар", "Аль-Мутаффифин", "Аль-Иншикак", "Аль-Бурудж", "Ат-Тарик", "Аль-Аля", "Аль-Гашия", "Аль-Фаджр", "Аль-Балад", "Аш-Шамс", "Аль-Лейл", "Ад-Духа", "Аш-Шарх", "Ат-Тин", "Аль-Алак", "Аль-Кадр", "Аль-Баййина", "Аз-Зальзаля", "Аль-Адият", "Аль-Кариа", "Ат-Такасур", "Аль-Аср", "Аль-Хумаза", "Аль-Филь", "Курайш", "Аль-Маун", "Аль-Каусар", "Аль-Кафирун", "Ан-Наср", "Аль-Масад", "Аль-Ихлас", "Аль-Фаляк", "Ан-Нас"]

def get_json(url):
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (ummati-bot)", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print("сеть:", url.split("?")[0], e); time.sleep(5 * (i + 1))
    return None

def ayah(n):
    """Аят по сквозному номеру 1..6236 -> (сура, аят, перевод Кулиева) или None. В казахском режиме — перевод Алтая."""
    if kk.ON:
        return kk.by_num(n)
    d = get_json(f"https://api.alquran.cloud/v1/ayah/{n}/ru.kuliev")
    if not d or d.get("data", {}).get("edition", {}).get("identifier") != "ru.kuliev":
        return None
    d = d["data"]
    return d["surah"]["number"], d["numberInSurah"], d["text"].replace(" - ", " — ").strip()

def chunks(text, limit=260):
    """Режем длинный текст на куски до limit символов по границам предложений (слова не меняются)."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return [text]
    pieces = []
    for p in re.split(r"(?<=[.!?;:»])\s+", text):
        while len(p) > limit:
            cut = p.rfind(", ", 0, limit)
            if cut < limit * 0.4:
                cut = p.rfind(" ", 0, limit)
            pieces.append(p[:cut + 1].strip()); p = p[cut + 1:].strip()
        pieces.append(p)
    out, cur = [], ""
    for p in pieces:
        if cur and len(cur) + 1 + len(p) > limit:
            out.append(cur); cur = p
        else:
            cur = (cur + " " + p).strip()
    if cur:
        out.append(cur)
    return out

def show(piece, i, n):
    """Кусок -> текст для карточки: «…» на стыках, внутренние кавычки «» -> „“ (как в post.py)."""
    s = piece.strip()
    if i < n - 1:
        s = s.rstrip(" ,;:—-")
        if not s.endswith(("…", "!", "?")):
            s = (s[:-1] if s.endswith(".") else s) + "…"
    if i > 0 or s[:1].islower():
        s = "…" + s.lstrip("…")
    out, depth = [], 0
    for ch in s:
        if ch == "«":
            depth += 1; out.append("„")
        elif ch == "»":
            if depth:
                depth -= 1; out.append("“")
        else:
            out.append(ch)
    s = "".join(out)
    if depth:
        s = s.replace("„", "", depth)
    return s

TAFSIR = "https://api.quran.com/api/v4/tafsirs/170/by_ayah/{}:{}"   # Тафсир ас-Саади, перевод Э. Кулиева

def excerpt(text, lo=200, hi=460):
    """Начало тафсира целыми предложениями (слова не меняются). None — если не удалось вырезать аккуратно."""
    t = " ".join(re.sub(r"<[^>]+>", " ", text).split())
    sents = re.split(r"(?<=[.!?])\s+(?=[А-ЯЁA-Z«(„\"])", t)
    out = ""
    for s in sents:
        if out and len(out) >= lo and out.count("«") == out.count("»") and out.count("(") == out.count(")"):
            break
        if len(out) + len(s) > 520:
            break
        out = (out + " " + s).strip()
    while out.endswith(":"):                      # «...и сказал:» — дальше идёт следующий аят, обрываем раньше
        cut = max(out.rfind(". "), out.rfind("! "), out.rfind("? "))
        out = out[:cut + 1].strip() if cut > 0 else ""
    if not out or out.count("«") != out.count("»") or out.count("(") != out.count(")") or len(out) > 520:
        return None
    return out

def tafsir(s, k):
    """Краткое пояснение к аяту s:k из тафсира ас-Саади -> (текст, подпись) или None.
    Если к самому аяту комментария нет (ас-Саади толкует группу аятов), берём ближайший предыдущий в суре."""
    for j in range(k, max(0, k - 6), -1):
        d = get_json(TAFSIR.format(s, j))
        text = ((d or {}).get("tafsir") or {}).get("text") or ""
        if text.strip():
            ex = excerpt(text)
            if not ex:
                return None
            where = f"{s}:{k}" if j == k else f"{s}:{j}–{k}"
            return ex, f"Тафсир ас-Саади к аяту {where}" if j == k else f"Тафсир ас-Саади к аятам {where}"
        if d is None:
            return None
    return None

def tafsir_card(s, k):
    t = tafsir(s, k)
    if not t:
        return None
    return (show(t[0], 0, 1), t[1], "Перевод Э. Кулиева, сокращено", "СМЫСЛ АЯТА")

def ayah_cards(n):
    """Карточки для аята n: [(цитата, источник, пояснение, kicker)], подпись, (сура, аят)."""
    a = ayah(n)
    if not a:
        return None
    s, k, text = a
    parts = chunks(text)
    if kk.ON:                                     # казахский: аят Алтая, без тафсира (казахского ас-Саади нет)
        src = kk.ref(s, k)
        cards = [(show(p, i, len(parts)), src + (f" · {i + 1}/{len(parts)}" if len(parts) > 1 else ""),
                  f"{kk.sura(s)}. {kk.SOURCE}", kk.K_QURAN) for i, p in enumerate(parts)]
        return cards, kk.caption(s, k) + "\n\n" + kk.TAGS + " #аят", (s, k)
    src = f"Коран, {s}:{k}"
    cards = [(show(p, i, len(parts)), src + (f" · {i + 1}/{len(parts)}" if len(parts) > 1 else ""),
              f"Сура «{NAMES[s - 1]}». Перевод смыслов Э. Кулиева", "СЛОВА ВСЕВЫШНЕГО") for i, p in enumerate(parts)]
    caption = f"Коран, сура «{NAMES[s - 1]}», аят {k}. Перевод смыслов Э. Кулиева.\n\n#коран #ислам #сура #аят #жайнамаз #намазныековрики"
    tc = tafsir_card(s, k)
    if tc:
        cards.append(tc)
        first = re.split(r"(?<=[.!?])\s+", tc[0])[0]
        extra = f"\n\nСмысл (тафсир ас-Саади): {first}"
        if len(caption) + len(extra) <= 490:
            caption = caption.replace("\n\n#коран", extra + "\n\n#коран")
    return cards, caption, (s, k)

def hadiths():
    return json.load(open("hadiths.json", encoding="utf-8"))

def hadith_parts(h):
    text = h["text"].replace("ﷺ", "(да благословит его Аллах и приветствует)").strip()
    intro = (h.get("intro") or "").strip()
    body = text[len(intro):].strip() if intro and text.startswith(intro) else text
    b = body.rstrip(".").strip()
    if b.startswith("«") and b.endswith("»") and b.count("«") == b.count("»"):
        body = b[1:-1]
    elif not intro:
        intro = ""
    return intro, body

def hadith_cards(h):
    intro, body = hadith_parts(h)
    parts = chunks(body)
    grade = h.get("grade") or "Хадис"
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    cards = [(show(p, i, len(parts)), grade + (f" · {i + 1}/{len(parts)}" if len(parts) > 1 else ""),
              attr, "ХАДИС") for i, p in enumerate(parts)]
    caption = ((intro + "\n\n") if intro else "") + f"{attr}. {grade}.\n\n#хадис #сунна #коран #ислам #сура #жайнамаз #намазныековрики"
    return cards, caption[:490]
