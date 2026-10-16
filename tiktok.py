"""TikTok: публикация готового ролика (videos/....mp4 + .json) через Content Posting API (Direct Post).
python tiktok.py videos/auto_2026-10-11T18.mp4   — публикация
python tiktok.py --auth КОД                      — первый вход: обменять код авторизации на токен

Секреты: TT_CLIENT_KEY, TT_CLIENT_SECRET. Refresh-токен хранится в репозитории в tt_token.enc,
зашифрованный (AES-256, ключ — TT_CLIENT_SECRET), и обновляется при каждом запуске.
Пока приложение не прошло аудит TikTok, видео публикуются только приватно (SELF_ONLY).
После аудита: переменная репозитория TT_AUDITED=1 — и ролики станут публичными."""
import base64, json, os, re, subprocess, sys, time, urllib.request, urllib.error

BRAND_TAGS = "#коран #ислам #сура #жайнамаз #намазныековрики"   # на всех видео во всех соцсетях

def tags_only(m):
    """Подпись к видео — только хэштеги (текст уже есть в самом ролике): общие + тематические, без повторов."""
    base = m.get("caption") or " ".join(t for t in re.findall(r"#\w+", m.get("description", "")) if t != "#shorts")
    out = []
    for t in (BRAND_TAGS + " " + base).split():
        if t not in out: out.append(t)
    return " ".join(out)

API = "https://open.tiktokapis.com/v2"
KEY = os.environ.get("TT_CLIENT_KEY", "").strip()
SECRET = os.environ.get("TT_CLIENT_SECRET", "").strip()
REDIRECT = "https://amocrm-proxy.github.io/ummati-threads/tiktok-callback.html"
STORE = "tt_token.enc"
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}

def req(url, data=None, headers=None, method=None, raw=False):
    h = {"User-Agent": "ummati-bot"}; h.update(headers or {})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method), timeout=120) as r:
                body = r.read()
                return body if raw else json.loads(body or b"{}")
        except urllib.error.HTTPError as e:
            msg = f"{method or ('POST' if data else 'GET')} {url.split('?')[0]}: {e.code} {e.read().decode()[:400]}"
            if e.code >= 500 and attempt < 2:
                print(msg, "— повтор"); time.sleep(20); continue
            raise RuntimeError(msg)

def crypt(data, decrypt=False):
    args = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-a", "-A", "-pass", "env:TT_CLIENT_SECRET"]
    if decrypt:
        args.insert(3, "-d")
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout

def put_file(path, raw, msg):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    body = {"message": msg, "content": base64.b64encode(raw).decode()}
    try:
        body["sha"] = req(url + "?ref=main", headers=GH_HDR)["sha"]
    except RuntimeError:
        pass
    req(url, data=json.dumps(body).encode(), headers=GH_HDR, method="PUT")

def oauth(**params):
    import urllib.parse
    d = req(f"{API}/oauth/token/", data=urllib.parse.urlencode(dict(client_key=KEY, client_secret=SECRET, **params)).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"})
    if "access_token" not in d:
        raise RuntimeError(f"TikTok токен: {d.get('error')} {d.get('error_description')}")
    put_file(STORE, crypt(d["refresh_token"].encode()), "tt_token")   # refresh-токен меняется — сохраняем новый
    return d

def access_token():
    if not os.path.exists(STORE):
        return None
    return oauth(grant_type="refresh_token", refresh_token=crypt(open(STORE, "rb").read(), decrypt=True).decode())["access_token"]

def api(path, tok, body):
    d = req(f"{API}/{path}", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"})
    if (d.get("error") or {}).get("code", "ok") != "ok":
        raise RuntimeError(f"{path}: {d['error']}")
    return d.get("data", {})

def publish(path):
    tok = access_token()
    if not tok:
        print("TikTok: ещё не подключён (нет tt_token.enc) — пропускаю"); return
    m = json.load(open(path.rsplit(".", 1)[0] + ".json", encoding="utf-8"))
    info = api("post/publish/creator_info/query/", tok, {})
    opts = info.get("privacy_level_options", [])
    privacy = "PUBLIC_TO_EVERYONE" if os.environ.get("TT_AUDITED") == "1" and "PUBLIC_TO_EVERYONE" in opts else "SELF_ONLY"
    title = (tags_only(m) + " #fyp")[:2150]
    size = os.path.getsize(path)
    src = {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}
    inbox = False
    try:
        d = api("post/publish/video/init/", tok, {
            "post_info": {"title": title, "privacy_level": privacy, "disable_duet": False,
                          "disable_comment": False, "disable_stitch": False, "video_cover_timestamp_ms": 1500},
            "source_info": src})
    except RuntimeError as e:
        if "unaudited_client" not in str(e):
            raise
        # до аудита TikTok не даёт публиковать в открытый аккаунт — кладём ролик в черновики (входящие) TikTok,
        # владелец публикует его из приложения одним нажатием
        print("TikTok: приложение ещё не прошло аудит — отправляю ролик в черновики TikTok")
        d = api("post/publish/inbox/video/init/", tok, {"source_info": src}); inbox = True
    req(d["upload_url"], data=open(path, "rb").read(), method="PUT", raw=True,
        headers={"Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": f"bytes 0-{size - 1}/{size}"})
    for _ in range(40):                           # TikTok обрабатывает видео — ждём до ~7 минут
        time.sleep(10)
        st = api("post/publish/status/fetch/", tok, {"publish_id": d["publish_id"]})
        if inbox and st.get("status") in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            print("TikTok: ролик в черновиках — откройте уведомление в приложении TikTok и нажмите «Опубликовать».",
                  "Подпись:", title[:150]); return
        if st.get("status") == "PUBLISH_COMPLETE":
            print("TikTok опубликован:", d["publish_id"], "| доступ:", privacy, "| ник:", info.get("creator_username")); return
        if st.get("status") == "FAILED":
            raise RuntimeError(f"TikTok: публикация не прошла: {st.get('fail_reason')}")
    print("TikTok: видео ещё обрабатывается, publish_id", d["publish_id"])

if __name__ == "__main__":
    if not KEY or not SECRET:
        print("TikTok: нет TT_CLIENT_KEY / TT_CLIENT_SECRET — пропускаю"); sys.exit(0)
    if sys.argv[1] == "--auth":
        d = oauth(grant_type="authorization_code", code=sys.argv[2].strip(), redirect_uri=REDIRECT)
        print("TikTok подключён. open_id:", d.get("open_id"), "| права:", d.get("scope"))
    else:
        publish(sys.argv[1])
