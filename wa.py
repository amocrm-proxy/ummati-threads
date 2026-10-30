"""WhatsApp-канал Ummati (вручную): 3 раза в день бот в Telegram присылает Арсену готовый пост —
картинку и отдельным сообщением текст. Арсен пересылает картинку в канал и вставляет текст.
Порядок по кругу: аят → сүннет → әдеп → дұға → жүрекке демеу → жайнамаз (продажа).
Всё на казахском. Аяты и дұға — дословно перевод Халифы Алтая (kk.py), сүннет/әдеп — sunnet_kk.json,
дұға — только из Құрана (duas_kk.json, транскрипцию проверяет Арсен). Состояние — wa_state.json.
Вызывается из post.py в 09, 14 и 20 часов (Алматы)."""
import datetime, io, json, os, sys, urllib.request, uuid
import kk, support
import ig_render as R

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "wa_state.json")
sys.path.insert(0, os.path.join(HERE, "shop"))
import shop
HOURS = (9, 14, 20)
ORDER = ["ayah", "sunna", "adab", "dua", "support", "sale"]
PHONE = "77078342525"
FOOT = f"—\nЖайнамаздарды көру: instagram.com/ummati.family\nТапсырыс: wa.me/{PHONE}"
LINKS = ("Instagram: instagram.com/ummati.family\nThreads: threads.net/@ummati.family\n"
         "TikTok: tiktok.com/@ummati.family")

def _ayah_text(ref):
    s, a = ref.split(":")
    lo, hi = (a.split("-") + [a])[:2]
    return int(s), int(lo), " ".join(kk.text(int(s), x) for x in range(int(lo), int(hi) + 1))

def ayah(k):
    bank = [b["ref"] for b in json.load(open(os.path.join(HERE, "bank.json"), encoding="utf-8")) if not b.get("q")]
    for j in range(80):                                   # короткие аяты, чтобы читались на картинке
        s, a = kk.parse_ref(bank[(k + j) % len(bank)])
        t = kk.text(s, a)
        if len(t) <= 260 and "Б.Ж.М" not in t:
            im = R.text_slide("emer", kk.K_QURAN, quote=t, source=kk.ref(s, a), body=kk.SOURCE)
            return im, f"📖 Құран Кәрім\n\n«{t}»\n\n{kk.caption(s, a)}\n\n{FOOT}", j + 1
    raise SystemExit("нет короткого аята")

def sunnet(cat, k):
    pool = [c for c in json.load(open(os.path.join(HERE, "sunnet_kk.json"), encoding="utf-8")) if c["cat"] == cat]
    c = pool[k % len(pool)]
    kick = "СҮННЕТ" if cat == "sunna" else "ӘДЕП"
    lines = "\n".join(("• " if len(c["lines"]) > 1 else "") + x for x in c["lines"])
    im = R.text_slide("cream", kick, title=c["title"], body=lines + f"\n\n({c['src']})")
    return im, f"{kick}\n\n{c['title']}\n{lines}\n\n({c['src']})\n\n{FOOT}", 1

def dua(k):
    D = json.load(open(os.path.join(HERE, "duas_kk.json"), encoding="utf-8"))
    d = D[k % len(D)]
    s, a, t = _ayah_text(d["ref"])
    where = f"«{kk.NAMES[s - 1]}» сүресі, {d['ref'].split(':')[1]}-аят"
    im = R.text_slide("choc", "ҚҰРАНДАҒЫ ДҰҒА", title=d["tr"], source=f"Құран, {d['ref']}", body=f"Мағынасы: {t}")
    cap = (f"🤲 Құрандағы дұға\n\n{d['tr']}\n\nАяттың мағынасы: «{t}»\n({where}. {kk.SOURCE})\n\n"
           f"Сақтап, жақындарыңызға жіберіңіз.\n\n{FOOT}")
    return im, cap, 1

def demeu(k):
    x = support.item(k)
    _, s, a, t, _ = x
    im = R.text_slide("night", kk.K_SUPPORT, quote=t, source=kk.ref(s, a), body=kk.SOURCE)
    return im, f"🤍 Жүрекке демеу\n\n«{t}»\n\n{kk.caption(s, a)}\n\n{FOOT}", 1

def sale(k, day):
    ims, cap = shop.carousel(day, k)
    cap = cap.replace("Тапсырыс беру үшін директке жазыңыз 🤍", f"Тапсырыс беру үшін WhatsApp-қа жазыңыз 🤍\nwa.me/{PHONE}")
    cap = cap.rsplit("\n\n#", 1)[0] + "\n\n" + LINKS
    return ims[0], cap, 1

def build(st, day):
    kind = ORDER[st.get("i", 0) % len(ORDER)]
    k = st.get(kind, 0)
    if kind == "ayah":
        im, cap, step = ayah(k)
    elif kind in ("sunna", "adab"):
        im, cap, step = sunnet(kind, k)
    elif kind == "dua":
        im, cap, step = dua(k)
    elif kind == "support":
        im, cap, step = demeu(k)
    else:
        im, cap, step = sale(k, day)
    st[kind] = k + step
    st["i"] = st.get("i", 0) + 1
    return kind, im, cap

def _send_photo(token, chat, jpg, caption):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat}\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n"
            f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"wa.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n"
            ).encode() + jpg + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    urllib.request.urlopen(req, timeout=60).read()

def _send_text(token, chat, text):
    data = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data,
                                                  headers={"Content-Type": "application/json"}), timeout=60).read()

def run(put_file, now, dry=False):
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"sale": 6}   # продажи начинаем с новых фото (флэтлеи)
    kind, im, cap = build(st, now.date())
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
    if dry:
        return kind, buf.getvalue(), cap
    token = os.environ["TG_TOKEN"].strip()
    owner = json.load(open(os.path.join(HERE, "tg_state.json"), encoding="utf-8"))["owner"]
    n = st["i"]
    _send_photo(token, owner, buf.getvalue(), f"WhatsApp-канал · {n} · {now:%d.%m %H:%M} — картинка (переслать в канал)")
    _send_text(token, owner, cap)
    raw = json.dumps(st, ensure_ascii=False, indent=1).encode()
    open(STATE, "wb").write(raw)
    put_file("wa_state.json", raw, f"wa {now:%Y-%m-%dT%H}")
    print("WhatsApp-канал:", kind, "отправлено в Telegram")
