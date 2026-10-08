"""Автопостинг ummati в Threads.
Берёт из schedule.json пост на текущий час (Алматы).
- если у поста есть "image" — публикует готовую картинку из репозитория;
- если есть "quote"/"source"/"explain" — рисует карточку (render.py), кладёт её в папку cards/ репозитория и публикует.
"""
import base64, json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error
from zoneinfo import ZoneInfo

API = "https://graph.threads.net/v1.0"
TOKEN = os.environ["THREADS_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")

def http(method, url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Ошибка {method} {url.split('?')[0]} {e.code}: {e.read().decode()}")

def threads(method, path, **params):
    params["access_token"] = TOKEN
    q = urllib.parse.urlencode(params)
    if method == "GET":
        return http("GET", f"{API}/{path}?{q}")
    return http("POST", f"{API}/{path}", data=q.encode())

def upload_to_repo(path, raw):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    hdr = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {"message": f"card {path}", "content": base64.b64encode(raw).decode()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=30) as r:
            payload["sha"] = json.load(r)["sha"]
    except urllib.error.HTTPError:
        pass
    http("PUT", url, data=json.dumps(payload).encode(), headers=hdr)

slot = os.environ.get("SLOT") or datetime.datetime.now(ZoneInfo("Asia/Almaty")).strftime("%Y-%m-%dT%H:00")
dry = slot.startswith("dry:")
slot = slot[4:] if dry else slot
schedule = json.load(open("schedule.json", encoding="utf-8"))
post = schedule.get(slot)
if not post:
    print(f"На {slot} ничего не запланировано")
    sys.exit(0)

if post.get("image"):
    image_path = post["image"]
else:
    import io, subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
    from render import render
    hour = int(slot[11:13])
    img = render(post["quote"], post["source"], post.get("explain", ""), hour)
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=90)
    image_path = f"cards/{slot.replace(':', '-')}.jpg"
    upload_to_repo(image_path, buf.getvalue())
    time.sleep(5)

image_url = f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(image_path)}"
if dry:
    print("DRY", image_url)
    sys.exit(0)
text = post.get("text") or post.get("explain", "")
user_id = threads("GET", "me", fields="id")["id"]
container = threads("POST", f"{user_id}/threads", media_type="IMAGE", image_url=image_url, text=text)
time.sleep(30)
result = threads("POST", f"{user_id}/threads_publish", creation_id=container["id"])
print(f"Опубликовано {slot}: {image_path} -> {result}")
