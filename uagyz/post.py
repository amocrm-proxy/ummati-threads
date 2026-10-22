"""Уағыз: публикует следующий готовый ролик (uagyz/<тег>/clips/*.mp4) в Instagram страницы уағыз как Reels.
Ключ — секрет UAGYZ_IG_TOKEN (бессрочный ключ страницы Facebook, к которой привязан этот Instagram).
Очередь — по порядку тегов и номеров; опубликованные записываются в uagyz/posted.json.
Без UAGYZ_IG_TOKEN ролик с готовой подписью уходит владельцу в Telegram (бот TG_TOKEN), публикует он сам.
`python uagyz/post.py yt` — следующий ролик на YouTube-канал Ummati (своя очередь в uagyz/yt_posted.json).
Лимит YouTube API — 10 000 единиц в сутки, загрузка = 1600: Ummati грузит 5 роликов, уағыз — 1 (18:00)."""
import glob, json, os, sys, time, urllib.parse, urllib.request, urllib.error

G = "https://graph.facebook.com/v21.0"
TOKEN = os.environ.get("UAGYZ_IG_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "posted.json")
YT_STATE = os.path.join(HERE, "yt_posted.json")
TAGS = "#уағыз #ислам #құран #намаз #иман #дін #қазақша"

def call(method, path, **params):
    params["access_token"] = TOKEN
    q = urllib.parse.urlencode(params)
    url = f"{G}/{path}" + (f"?{q}" if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else q.encode(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:400]}")

def ig_user():
    me = call("GET", "me", fields="id,name,instagram_business_account")
    if me.get("instagram_business_account"):
        return me["instagram_business_account"]["id"], me.get("name")
    for p in call("GET", "me/accounts", fields="id,name,instagram_business_account").get("data", []):
        if p.get("instagram_business_account"):
            print("ВНИМАНИЕ: в UAGYZ_IG_TOKEN ключ пользователя, а не страницы — он истечёт.")
            return p["instagram_business_account"]["id"], p["name"]
    sys.exit("К ключу не привязан ни один Instagram (проверь связку страницы и Instagram)")

def check():
    info = call("GET", "debug_token", input_token=TOKEN).get("data", {})
    exp = info.get("expires_at", 0)
    uid, page = ig_user()
    acc = call("GET", uid, fields="username,followers_count")
    print("Ключ:", info.get("type"), "| истекает:", "никогда" if not exp else time.strftime("%d/%m/%Y", time.gmtime(exp)))
    print("Страница:", page, "| Instagram:", acc.get("username"), "| подписчики:", acc.get("followers_count"))
    return uid

def queue(state=STATE):
    """Следующий ролик: видео чередуются по кругу (после ролика из одного видео — следующее видео, где ещё есть ролики)."""
    posted = json.load(open(state)) if os.path.exists(state) else []
    tags = sorted(glob.glob(os.path.join(HERE, "uagyz-*")), key=lambda p: int(p.rsplit("-", 1)[-1]) if p.rsplit("-", 1)[-1].isdigit() else 0)
    ready = []                                    # [(папка, cfg, первый неопубликованный ролик, путь)]
    for tag_dir in tags:
        cfg_p = os.path.join(tag_dir, "clips.json")
        if not os.path.exists(cfg_p):
            continue
        cfg = json.load(open(cfg_p, encoding="utf-8"))
        for c in cfg["clips"]:
            rel = os.path.relpath(os.path.join(tag_dir, "clips", f"{c['id']}.mp4"), os.path.join(HERE, ".."))
            if rel not in posted and os.path.exists(os.path.join(HERE, "..", rel)):
                ready.append((os.path.basename(tag_dir), cfg, c, rel)); break
    if not ready:
        return None, None, None, posted
    num = lambda name: int(name.rsplit("-", 1)[-1]) if name.rsplit("-", 1)[-1].isdigit() else 0
    last = num(posted[-1].split("/")[1]) if posted else 0
    later = [r for r in ready if num(r[0]) > last]
    pick = min(later or ready, key=lambda r: num(r[0]))
    return pick[3], pick[1], pick[2], posted

def telegram(path, caption):
    """Отправить ролик владельцу бота (tg_state.json -> owner) с подписью для копирования."""
    import uuid
    tok = os.environ.get("TG_TOKEN", "").strip()
    owner = json.load(open(os.path.join(HERE, "..", "tg_state.json"))).get("owner")
    if not tok or not owner:
        sys.exit("Нет TG_TOKEN или владельца бота — некуда отправить ролик")
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("chat_id", str(owner)), ("caption", caption[:1000]), ("supports_streaming", "true")):
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"{os.path.basename(path)}\"\r\n"
                 "Content-Type: video/mp4\r\n\r\n".encode() + open(path, "rb").read() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendVideo", data=b"".join(parts), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["ok"]

def youtube():
    """Следующий ролик уағыз — Shorts на канал Ummati (ключи YT_* те же, что у роликов Ummati)."""
    sys.path.insert(0, os.path.join(HERE, ".."))
    import yt
    rel, cfg, c, posted = queue(YT_STATE)
    if not rel:
        print("YouTube: очередь пуста"); return
    who = cfg.get("ustaz") or ""
    title = " | ".join(x for x in (c.get("topic"), who) if x) or "Уағыз"
    desc = "\n".join(x for x in (c.get("topic"), who or cfg.get("caption") or "Ұстаздардың уағызы") if x) + "\n\n" + TAGS + " #shorts\n\nЖайнамаздар: instagram.com/ummati.family"
    tags = ["уағыз", "ислам", "құран", "намаз", "иман", "қазақша", "ummati", "shorts"] + ([who] if who else [])
    yt.upload(os.path.join(HERE, "..", rel), title + " #shorts", desc, "public", tags, lang="kk", audio="kk")
    posted.append(rel)
    json.dump(posted, open(YT_STATE, "w"), indent=1)

def main():
    if not TOKEN:                                 # Instagram ещё не подключён — отправляем ролик в Telegram
        rel, cfg, c, posted = queue()
        if not rel:
            print("Очередь пуста — новых роликов нет"); return
        caption = (c.get("caption") or "\n".join(x for x in (c.get("topic"), cfg.get("caption") or cfg.get("ustaz") or "Ұстаздардың уағызы") if x)) + "\n\n" + TAGS + "\n\nЖайнамаздар: @ummati.family"
        print("Telegram:", rel, telegram(os.path.join(HERE, "..", rel), caption))
        posted.append(rel)
        json.dump(posted, open(STATE, "w"), indent=1)
        return
    uid = check()
    if os.environ.get("CHECK_ONLY"):
        return
    rel, cfg, c, posted = queue()
    if not rel:
        print("Очередь пуста — новых роликов нет"); return
    url = f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(rel)}"
    caption = (c.get("caption") or "\n".join(x for x in (c.get("topic"), cfg.get("caption") or cfg.get("ustaz") or "Ұстаздардың уағызы") if x)) + "\n\n" + TAGS + "\n\nЖайнамаздар: @ummati.family"
    cid = call("POST", f"{uid}/media", media_type="REELS", video_url=url, caption=caption, share_to_feed="true")["id"]
    for _ in range(60):
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            sys.exit(f"Instagram не принял видео {rel}")
        time.sleep(5)
    else:
        sys.exit("Видео не обработалось за 5 минут")
    print("Опубликовано:", rel, call("POST", f"{uid}/media_publish", creation_id=cid))
    posted.append(rel)
    json.dump(posted, open(STATE, "w"), indent=1)

if __name__ == "__main__":
    youtube() if sys.argv[1:] == ["yt"] else main()
