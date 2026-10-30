"""Загрузка видео на YouTube-канал Ummati.
python yt.py videos/112.mp4 [public|unlisted|private]
Ключи: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN (секреты GitHub).
Пока проект Google не прошёл аудит, YouTube сам делает видео приватными."""
import json, os, re, sys, urllib.request, urllib.parse, urllib.error

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

def token():
    data = urllib.parse.urlencode({
        "client_id": os.environ["YT_CLIENT_ID"].strip(), "client_secret": os.environ["YT_CLIENT_SECRET"].strip(),
        "refresh_token": os.environ["YT_REFRESH_TOKEN"].strip().strip('"'), "grant_type": "refresh_token"}).encode()
    try:
        with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as r:
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        sys.exit(f"Google не выдал доступ ({e.code}): {e.read().decode()[:300]}")

def upload(path, title, desc, privacy="public", tags=None, lang="ru", audio="ar"):
    tok = token()
    desc = desc.rstrip() + "\n\nWhatsApp арнамызға жазылыңыз: https://whatsapp.com/channel/0029Vb9Npdf1CYoVbO88ZX3Q"   # ссылка на WhatsApp-канал во всех видео YouTube
    meta = {"snippet": {"title": title[:100], "description": desc[:4900], "categoryId": "22",
                        "tags": tags or ["ummati", "құран", "намаз", "ислам", "жайнамаз", "shorts"],
                        "defaultLanguage": lang, "defaultAudioLanguage": audio},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    size = os.path.getsize(path)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(), method="POST",
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            loc = r.headers["Location"]
        put = urllib.request.Request(loc, data=open(path, "rb").read(), method="PUT",
                                     headers={"Content-Type": "video/mp4"})
        with urllib.request.urlopen(put, timeout=600) as r:
            v = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"YouTube ошибка {e.code}: {e.read().decode()[:600]}")
    print("YouTube загружено:", f"https://youtube.com/shorts/{v['id']}", "| статус:", v["status"]["privacyStatus"])
    return v["id"]

if __name__ == "__main__":
    # python yt.py videos/112.mp4 [privacy] — заголовок и описание берутся из videos/112.json
    path = sys.argv[1]
    m = json.load(open(path.rsplit(".", 1)[0] + ".json", encoding="utf-8"))
    upload(path, m["title"], tags_only(m) + " #shorts", sys.argv[2] if len(sys.argv) > 2 else "public")
