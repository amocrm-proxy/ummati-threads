"""Автопостинг ummati в Threads: публикует пост, запланированный на текущий час (Алматы)."""
import json, os, sys, time, datetime, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

API = "https://graph.threads.net/v1.0"
TOKEN = os.environ["THREADS_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]

def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Ошибка API {e.code}: {e.read().decode()}")

slot = os.environ.get("SLOT") or datetime.datetime.now(ZoneInfo("Asia/Almaty")).strftime("%Y-%m-%dT%H:00")
schedule = json.load(open("schedule.json", encoding="utf-8"))
post = schedule.get(slot)
if not post:
    print(f"На {slot} ничего не запланировано")
    sys.exit(0)

user_id = call("GET", "me", fields="id")["id"]
image_url = f"https://raw.githubusercontent.com/{REPO}/main/img/{urllib.parse.quote(post['image'])}"
container = call("POST", f"{user_id}/threads", media_type="IMAGE", image_url=image_url, text=post.get("text", ""))
time.sleep(30)
result = call("POST", f"{user_id}/threads_publish", creation_id=container["id"])
print(f"Опубликовано {slot}: {post['image']} -> {result}")
