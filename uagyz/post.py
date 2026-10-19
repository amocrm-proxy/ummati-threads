"""Уағыз: публикует следующий готовый ролик (uagyz/<тег>/clips/*.mp4) в Instagram страницы уағыз как Reels.
Ключ — секрет UAGYZ_IG_TOKEN (бессрочный ключ страницы Facebook, к которой привязан этот Instagram).
Очередь — по порядку тегов и номеров; опубликованные записываются в uagyz/posted.json.
Без UAGYZ_IG_TOKEN ролик с готовой подписью уходит владельцу в Telegram (бот TG_TOKEN), публикует он сам."""
import glob, json, os, sys, time, urllib.parse, urllib.request, urllib.error

G = "https://graph.facebook.com/v21.0"
TOKEN = os.environ.get("UAGYZ_IG_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "posted.json")
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

def queue():
    posted = json.load(open(STATE)) if os.path.exists(STATE) else []
    for tag_dir in sorted(glob.glob(os.path.join(HERE, "uagyz-*")), key=lambda p: int(p.rsplit("-", 1)[-1]) if p.rsplit("-", 1)[-1].isdigit() else 0):
        cfg_p = os.path.join(tag_dir, "clips.json")
        if not os.path.exists(cfg_p):
            continue
        cfg = json.load(open(cfg_p, encoding="utf-8"))
        for c in cfg["clips"]:
            rel = os.path.relpath(os.path.join(tag_dir, "clips", f"{c['id']}.mp4"), os.path.join(HERE, ".."))
            if rel not in posted and os.path.exists(os.path.join(HERE, "..", rel)):
                return rel, cfg, c, posted
    return None, None, None, posted

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

def main():
    if not TOKEN:                                 # Instagram ещё не подключён — отправляем ролик в Telegram
        rel, cfg, c, posted = queue()
        if not rel:
            print("Очередь пуста — новых роликов нет"); return
        caption = (c.get("caption") or cfg["ustaz"]) + "\n\n" + TAGS + "\n\nЖайнамаздар: @ummati.family"
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
    caption = (c.get("caption") or cfg["ustaz"]) + "\n\n" + TAGS + "\n\nЖайнамаздар: @ummati.family"
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
    main()
