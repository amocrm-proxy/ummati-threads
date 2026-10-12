"""Telegram-бот рубрики «Размышление»: Арсен присылает голосовые к аятам, бот кладёт их в voices/.
Запускается из post.py каждый час. Нужен секрет TG_TOKEN (токен от @BotFather).
Владелец — тот, кто первым написал боту /start (дальше бот слушает только его).
По воскресеньям в 20:00 бот присылает 7 аятов на следующую неделю. Ответь голосовым на сообщение
с аятом (или просто пришли голосовое — оно встанет к первому аяту без записи)."""
import json, os, sys, time, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo
import content as C

TOKEN = os.environ.get("TG_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
STATE = "tg_state.json"

def tg(method, **p):
    data = urllib.parse.urlencode({k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in p.items()}).encode()
    with urllib.request.urlopen(urllib.request.Request(f"{API}/{method}", data=data), timeout=40) as r:
        return json.load(r)["result"]

def load():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {"offset": 0, "owner": None, "asked": {}, "voices": {}, "used": [], "week": ""}

def save(st, put_file):
    raw = json.dumps(st, ensure_ascii=False, indent=1).encode()
    open(STATE, "wb").write(raw)
    put_file(STATE, raw, "tg_state")

def candidates(st):
    """Аяты для размышлений: целые аяты из нашего банка (bank.json), которых ещё не было."""
    done = set(st["voices"]) | set(st["used"]) | {v for v in st["asked"].values()}
    return [b["ref"] for b in json.load(open("bank.json", encoding="utf-8")) if not b.get("q") and b["ref"] not in done]

def script(ref):
    """Текст для записи голосом: арабский, транслитерация (для заучивания), перевод Кулиева и смысл из тафсира ас-Саади."""
    def ed(e):
        d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{ref}/{e}")
        return d["data"]["text"].strip() if d else ""
    ar, tr, ru = ed("quran-uthmani"), ed("en.transliteration"), ed("ru.kuliev").replace(" - ", " — ")
    s, a = map(int, ref.split(":"))
    t = C.tafsir(s, a)
    parts = [f"Коран, {ref}", ar, f"Транслитерация: {tr}" if tr else "", "",
             "🎙 ТЕКСТ ДЛЯ ЗАПИСИ (читай спокойно, 30–50 секунд):",
             f"1) Перевод смыслов (Кулиев): «{ru}»"]
    if t:
        parts.append(f"2) Смысл ({t[1]}, пер. Кулиева): {t[0]}")
    parts.append(f"{3 if t else 2}) Одним предложением от себя: что ты возьмёшь из этого аята сегодня.")
    return "\n".join(p for p in parts if p is not None)

def send_week(st):
    refs = candidates(st)[:7]
    tg("sendMessage", chat_id=st["owner"], text=(
        "Ассаляму алейкум! Аяты на неделю для рубрики «Размышление».\n\n"
        "Под каждым аятом — текст для записи. Ответь голосовым на сообщение с аятом (свайп влево → ответить) "
        "и прочитай текст. Арабский и транслитерация — чтобы заучивать, читать их в записи не обязательно.\n"
        "Ролик с твоим голосом выходит каждый день в 18:00."))
    for ref in refs:
        m = tg("sendMessage", chat_id=st["owner"], text=script(ref))
        st["asked"][str(m["message_id"])] = ref
        time.sleep(1)

def resend_scripts(st):
    """Один раз: дослать тексты для записи к уже отправленным аятам (ответом на исходное сообщение)."""
    for mid, ref in list(st["asked"].items()):
        if ref in st["voices"] or ref in st["used"]:
            continue
        m = tg("sendMessage", chat_id=st["owner"], text=script(ref), reply_to_message_id=int(mid))
        st["asked"][str(m["message_id"])] = ref
        time.sleep(1)

def run(put_file, now):
    if not TOKEN:
        return
    st = load()
    changed = False
    ups = tg("getUpdates", offset=st["offset"], timeout=0)
    print("Telegram: бот @" + tg("getMe").get("username", "?"), "| новых сообщений:", len(ups), "| владелец задан:", bool(st["owner"]))
    for u in ups:
        st["offset"] = u["update_id"] + 1; changed = True
        msg = u.get("message") or {}
        chat = msg.get("chat", {}).get("id")
        print("Telegram: обновление", [k for k in u if k != "update_id"], msg.get("chat", {}).get("type"), (msg.get("text") or "")[:10])
        if st["owner"] is None and chat and msg.get("chat", {}).get("type") == "private":   # первый написавший = владелец
            st["owner"] = chat
            send_week(st); st["week"] = now.strftime("%G-%V")
            continue
        if chat != st["owner"]:
            continue
        audio = msg.get("voice") or msg.get("audio")
        if audio:
            reply = str((msg.get("reply_to_message") or {}).get("message_id", ""))
            ref = st["asked"].get(reply)
            if not ref:                                   # без ответа — к первому аяту без записи
                pend = [r for r in st["asked"].values() if r not in st["voices"] and r not in st["used"]]
                ref = pend[0] if pend else None
            if not ref:
                tg("sendMessage", chat_id=chat, text="Не понял, к какому аяту это голосовое. Ответь им на сообщение с аятом.")
                continue
            fp = tg("getFile", file_id=audio["file_id"])["file_path"]
            with urllib.request.urlopen(f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=60) as r:
                raw = r.read()
            path = f"voices/{ref.replace(':', '_')}.ogg"
            os.makedirs("voices", exist_ok=True); open(path, "wb").write(raw)
            put_file(path, raw, f"voice {ref}")
            st["voices"][ref] = path
            left = len([r for r in st["asked"].values() if r not in st["voices"] and r not in st["used"]])
            tg("sendMessage", chat_id=chat, reply_to_message_id=msg["message_id"],
               text=f"Записал для {ref}. В очереди роликов: {len([r for r in st['voices'] if r not in st['used']])}. Осталось записать: {left}.")
        elif msg.get("text", "").startswith("/list"):
            send_week(st)
    if st["owner"] and st.get("v", 1) < 2:
        resend_scripts(st); st["v"] = 2; changed = True
    if st["owner"] and now.weekday() == 6 and now.hour == 20 and st.get("week") != (now + datetime.timedelta(days=1)).strftime("%G-%V"):
        send_week(st); st["week"] = (now + datetime.timedelta(days=1)).strftime("%G-%V"); changed = True
    if changed:
        save(st, put_file)

def next_voice():
    """Для post.py: первый аят с записанным голосом, который ещё не выходил."""
    st = load()
    for ref, path in st["voices"].items():
        if ref not in st["used"] and os.path.exists(path):
            return ref
    return None

def mark_used(ref, put_file):
    st = load(); st["used"].append(ref); save(st, put_file)
