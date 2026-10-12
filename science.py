"""Рубрика «Аят и наука»: каждый день в 12:00 одна карусель в Instagram и Threads.
Темы — science.json (идут по кругу по дате). Текст аятов каждый раз скачивается заново (перевод Э. Кулиева);
если перевод не получен — публикация пропускается, своими словами аяты не пишем."""
import json, datetime
import content as C

START = datetime.date(2026, 10, 14)
HOUR = 12
TAGS = "#коран #наука #ислам #аятинаука #ummati"

def entry(slot):
    S = json.load(open("science.json", encoding="utf-8"))
    d = (datetime.date.fromisoformat(slot[:10]) - START).days
    return S[d % len(S)] if d >= 0 else None

def kuliev(ref):
    d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev")
    if not d or d.get("data", {}).get("edition", {}).get("identifier") != "ru.kuliev":
        return None
    return d["data"]["text"].replace(" - ", " — ").strip()

def refs_label(refs):
    s = refs[0].split(":")[0]
    a = [r.split(":")[1] for r in refs]
    return f"{s}:{a[0]}" + (f"–{a[-1]}" if len(a) > 1 else "")

def build(e):
    """-> (картинки 1080x1350, подпись для Instagram, текст для Threads) или None."""
    import ig_render as R
    texts = [kuliev(r) for r in e["refs"]]
    if not all(texts):
        return None
    label = refs_label(e["refs"])
    pieces = []                                   # (цитата, источник) — аяты подряд, длинные режем по предложениям
    for r, t in zip(e["refs"], texts):
        parts = C.chunks(t, 300)
        pieces += [(C.show(p, i, len(parts)), f"Коран, {r}") for i, p in enumerate(parts)]
    n = 1 + len(pieces) + 2
    ims = [R.text_slide("emer", "Аят и наука", title=e["hook"], body="Листайте →", page=f"1/{n}")]
    for i, (q, src) in enumerate(pieces, 2):
        ims.append(R.text_slide("cream", "Слова Всевышнего", quote=q, source=src,
                                body="Перевод смыслов Э. Кулиева", page=f"{i}/{n}"))
    ims.append(R.text_slide("choc", "Что открыла наука", title=e["big"], body=e["fact"], page=f"{n - 1}/{n}"))
    ims.append(R.text_slide("emer", "Задумайтесь", title=None, body=e["note"] + "\n\nИсточник: " + e["source"],
                            page=f"{n}/{n}", footer="Сохраните и поделитесь"))
    caption = (f"{e['hook']}\n\nКоран, {label}. Перевод смыслов Э. Кулиева.\n\n{e['fact']}\n\n{e['note']}\n\n"
               f"Источник: {e['source']}\n\n{TAGS}")
    threads = f"{e['hook']}\n\nКоран, {label} и что об этом знает наука. Листайте карусель.\n\nИсточник: {e['source']}"[:490]
    return ims, caption, threads
