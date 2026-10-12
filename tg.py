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

def send_week(st):
    refs = candidates(st)[:7]
    tg("sendMessage", chat_id=st["owner"], text=(
        "Ассаляму алейкум! Аяты на неделю для рубрики «Размышление».\n\n"
        "Ответь голосовым на каждое сообщение ниже (свайп влево → ответить). 15–25 секунд: "
        "что этот аят значит для тебя и как его применить сегодня. Без пересказа перевода — он будет на экране.\n"
        "Ролик с твоим голосом выходит каждый день в 18:00."))
    for ref in refs:
        d = C.get_json(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev")
        text = d["data"]["text"].replace(" - ", " — ") if d else ""
        m = tg("sendMessage", chat_id=st["owner"], text=f"Коран, {ref}\n«{text}»")
        st["asked"][str(m["message_id"])] = ref
        time.sleep(1)

def run(put_file, now):
    if not TOKEN:
        return
    st = load()
    changed = False
    for u in tg("getUpdates", offset=st["offset"], timeout=0):
        st["offset"] = u["update_id"] + 1; changed = True
        msg = u.get("message") or {}
        chat = msg.get("chat", {}).get("id")
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
