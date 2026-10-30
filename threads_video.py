"""Публикует готовый ролик (videos/....mp4 + .json) в Threads как видео-пост.
python threads_video.py videos/auto_2026-10-16T09.mp4"""
import base64, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error

BRAND_TAGS = "#коран #ислам #сура #жайнамаз #намазныековрики"   # на всех видео во всех соцсетях
try:
    import kk
    if kk.ON: BRAND_TAGS = kk.TAGS                 # казахский режим — казахские хэштеги
except ImportError:
    pass

def tags_only(m):
    """Подпись к видео — только хэштеги (текст уже есть в самом ролике): общие + тематические, без повторов."""
    base = m.get("caption") or " ".join(t for t in re.findall(r"#\w+", m.get("description", "")) if t != "#shorts")
    out = []
    for t in (BRAND_TAGS + " " + base).split():
        if t not in out: out.append(t)
    return " ".join(out)

API = "https://graph.threads.net/v1.0"
import th_token                                     # ключ Threads с автопродлением
TOKEN = th_token.get()
REPO = os.environ["GITHUB_REPOSITORY"]
GH_HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}

def http(method, url, data=None, headers=None):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, method=method, headers=headers or {}), timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = f"{method} {url.split('?')[0]}: {e.code} {e.read().decode()[:300]}"
            if e.code >= 500 and k < 3:
                print(msg, "— повтор"); time.sleep(20); continue
            sys.exit(msg)

def threads(method, path, **p):
    p["access_token"] = TOKEN
    q = urllib.parse.urlencode(p)
    return http("GET", f"{API}/{path}?{q}") if method == "GET" else http("POST", f"{API}/{path}", data=q.encode())

def put_file(path, raw):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    body = {"message": f"threads {path}", "content": base64.b64encode(raw).decode()}
    try:
        body["sha"] = http("GET", url + "?ref=main", headers=GH_HDR)["sha"]
    except SystemExit:
        pass
    http("PUT", url, data=json.dumps(body).encode(), headers=GH_HDR)

def main(path):
    m = json.load(open(path.rsplit(".", 1)[0] + ".json", encoding="utf-8"))
    name = "igauto/thr_" + os.path.basename(path)
    put_file(name, open(path, "rb").read())
    time.sleep(10)
    video_url = f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(name)}"
    text = tags_only(m) + "\n\nWhatsApp арнамыз: https://whatsapp.com/channel/0029Vb9Npdf1CYoVbO88ZX3Q"
    uid = threads("GET", "me", fields="id")["id"]
    cid = threads("POST", f"{uid}/threads", media_type="VIDEO", video_url=video_url, text=text[:490])["id"]
    for _ in range(60):                           # видео обрабатывается — ждём до 5 минут
        st = threads("GET", cid, fields="status,error_message")
        if st.get("status") == "FINISHED":
            break
        if st.get("status") == "ERROR":
            sys.exit(f"Threads не принял видео: {st.get('error_message')}")
        time.sleep(5)
    else:
        sys.exit("Threads: видео не обработалось за 5 минут")
    print("Threads видео опубликовано:", threads("POST", f"{uid}/threads_publish", creation_id=cid))

if __name__ == "__main__":
    main(sys.argv[1])
