"""Автопостинг ummati в Instagram (карусели и сторис из ig_schedule.json).
Запускается из post.py каждый час. Публикует всё, что запланировано на текущий час (Алматы).
SLOT=dry:... — только проверка токена, без публикации."""
import json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error, base64
from zoneinfo import ZoneInfo

G = "https://graph.facebook.com/v21.0"
IG_USER = "17841478246747969"
PAGE_ID = "1369084289619381"
TOKEN = os.environ.get("IG_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
GH_HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}

def call(method, path, **params):
    q = urllib.parse.urlencode(params)
    url = f"{G}/{path}" + (f"?{q}" if method == "GET" else "")
    req = urllib.request.Request(url, data=None if method == "GET" else q.encode(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode()[:400]}")

def page_token():
    info = call("GET", "debug_token", input_token=TOKEN, access_token=TOKEN)["data"]
    exp = info.get("expires_at", 0)
    print("Токен:", info.get("type"), "| истекает:", "никогда" if not exp else datetime.datetime.fromtimestamp(exp).strftime("%d/%m/%Y"),
          "| права:", ",".join(info.get("scopes", [])))
    if info.get("type") == "PAGE":
        return TOKEN
    for p in call("GET", "me/accounts", fields="id,access_token", access_token=TOKEN).get("data", []):
        if p["id"] == PAGE_ID:
            print("ВНИМАНИЕ: в IG_TOKEN лежит токен пользователя, а не Страницы — он истечёт. Нужен бессрочный токен Страницы.")
            return p["access_token"]
    raise RuntimeError("Страница Ummati не найдена в токене")

def wait_ready(cid, tok):
    for _ in range(30):
        st = call("GET", cid, fields="status_code", access_token=tok).get("status_code")
        if st == "FINISHED":
            return
        if st == "ERROR":
            raise RuntimeError(f"контейнер {cid}: ERROR")
        time.sleep(5)
    raise RuntimeError(f"контейнер {cid} не готов")

def url(path):
    return f"https://raw.githubusercontent.com/{REPO}/main/{path}"

def publish(item, tok):
    imgs = item["images"]
    if item["type"] == "story":
        cid = call("POST", f"{IG_USER}/media", media_type="STORIES", image_url=url(imgs[0]), access_token=tok)["id"]
    elif len(imgs) == 1:
        cid = call("POST", f"{IG_USER}/media", image_url=url(imgs[0]), caption=item.get("caption", ""), access_token=tok)["id"]
    else:
        kids = []
        for im in imgs:
            k = call("POST", f"{IG_USER}/media", image_url=url(im), is_carousel_item="true", access_token=tok)["id"]
            kids.append(k)
        for k in kids:
            wait_ready(k, tok)
        cid = call("POST", f"{IG_USER}/media", media_type="CAROUSEL", children=",".join(kids),
                   caption=item.get("caption", ""), access_token=tok)["id"]
    wait_ready(cid, tok)
    return call("POST", f"{IG_USER}/media_publish", creation_id=cid, access_token=tok)

def save_used(used, msg):
    json.dump(used, open("used.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    api = f"https://api.github.com/repos/{REPO}/contents/used.json"
    body = {"message": msg, "content": base64.b64encode(json.dumps(used, ensure_ascii=False, indent=1).encode()).decode()}
    try:
        with urllib.request.urlopen(urllib.request.Request(api + "?ref=main", headers=GH_HDR), timeout=30) as r:
            body["sha"] = json.load(r)["sha"]
    except urllib.error.HTTPError:
        pass
    urllib.request.urlopen(urllib.request.Request(api, data=json.dumps(body).encode(), method="PUT", headers=GH_HDR), timeout=30)

def main():
    if not TOKEN:
        print("IG_TOKEN не задан"); return
    slot = os.environ.get("SLOT") or datetime.datetime.now(ZoneInfo("Asia/Almaty")).strftime("%Y-%m-%dT%H:00")
    dry = slot.startswith("dry:")
    slot = slot[4:] if dry else slot
    tok = page_token()
    if dry:
        print("IG: проверка токена ок:", call("GET", IG_USER, fields="username", access_token=tok)); return
    sched = json.load(open("ig_schedule.json", encoding="utf-8")) if os.path.exists("ig_schedule.json") else {}
    used = json.load(open("used.json", encoding="utf-8")) if os.path.exists("used.json") else {}
    hour = slot[:13]
    for key in sorted(k for k in sched if k[:13] == hour):
        if f"ig {key}" in used:
            print("IG уже опубликовано:", key); continue
        try:
            res = publish(sched[key], tok)
            print("IG опубликовано:", key, res)
            used[f"ig {key}"] = slot
            save_used(used, f"ig {key}")
        except Exception as e:
            print("IG ОШИБКА", key, e)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("IG ОШИБКА:", e)
