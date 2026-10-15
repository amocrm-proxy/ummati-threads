"""Рубрика «Слова поддержки»: только дословные аяты (перевод Э. Кулиева) и хадисы из hadiths.json —
подборка об утешении, терпении, надежде и милости Аллаха (support.json). От себя ничего не пишем.
item(k) -> ("ayah", сура, аят, текст, сквозной номер) | ("hadith", запись hadiths.json) | None"""
import json, os
import content as C

HERE = os.path.dirname(os.path.abspath(__file__))
KICKER = "СЛОВА ПОДДЕРЖКИ"

def items():
    return json.load(open(os.path.join(HERE, "support.json"), encoding="utf-8"))

def item(k):
    it = items()[k % len(items())]
    if "ayah" in it:
        d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{it['ayah']}/ru.kuliev")
        if not d or d.get("data", {}).get("edition", {}).get("identifier") != "ru.kuliev":
            return None
        d = d["data"]
        return ("ayah", d["surah"]["number"], d["numberInSurah"], d["text"].replace(" - ", " — ").strip(), d["number"])
    H = {h["id"]: h for h in C.hadiths()}
    h = H.get(it["hadith"])
    return ("hadith", h) if h else None

def plain(x):
    """Текст для текстового поста (Threads)."""
    if x[0] == "ayah":
        return f"«{x[3]}»\n\nКоран, сура «{C.NAMES[x[1] - 1]}», аят {x[2]}. Перевод смыслов Э. Кулиева."
    h = x[1]
    intro, body = C.hadith_parts(h)
    attr = h.get("attr", ""); attr = attr[:1].upper() + attr[1:]
    return (intro + "\n\n" if intro else "") + (f"«{body}»" if intro else body) + f"\n\n{attr}. {h.get('grade') or 'Хадис'}."

def cards(x):
    """Карточки [(цитата, источник, пояснение, kicker)] и подпись — как у аятов/хадисов, но с заголовком рубрики."""
    if x[0] == "ayah":
        _, s, a, text, _ = x
        parts = C.chunks(text)
        src = f"Коран, {s}:{a}"
        cs = [(C.show(p, i, len(parts)), src + (f" · {i + 1}/{len(parts)}" if len(parts) > 1 else ""),
               f"Сура «{C.NAMES[s - 1]}». Перевод смыслов Э. Кулиева", KICKER) for i, p in enumerate(parts)]
        return cs, f"Коран, сура «{C.NAMES[s - 1]}», аят {a}. Перевод смыслов Э. Кулиева.\n\n#коран #поддержка #ислам"
    cs, cap = C.hadith_cards(x[1])
    return [(q, src, ex, KICKER) for q, src, ex, _ in cs], cap.replace("#хадис", "#хадис #поддержка")
