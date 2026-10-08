"""Автопостинг ummati в Threads.
1) Если в schedule.json есть пост на текущий час (Алматы) — публикует его
   ("image" — готовая картинка, "quote/source/explain" — рисует карточку).
2) Если нет — берёт следующий неиспользованный аят из bank.json по времени суток.
   Текст аята каждый раз скачивается заново (перевод Э. Кулиева) и сверяется:
   фрагмент из банка обязан дословно совпасть с переводом, иначе аят пропускается.
   Использованные аяты записываются в used.json.
SLOT=dry:2026-10-10T16:00 — тест: рисует и кладёт карточку, но не публикует.
"""
import base64, io, json, os, re, subprocess, sys, time, datetime, urllib.request, urllib.parse, urllib.error
from zoneinfo import ZoneInfo

API = "https://graph.threads.net/v1.0"
TOKEN = os.environ["THREADS_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GH_HDR = {"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"}

def http(method, url, data=None, headers=None, fatal=True):
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = f"Ошибка {method} {url.split('?')[0]} {e.code}: {e.read().decode()}"
        if fatal:
            sys.exit(msg)
        print(msg)
        return None

def threads(method, path, **params):
    params["access_token"] = TOKEN
    q = urllib.parse.urlencode(params)
    if method == "GET":
        return http("GET", f"{API}/{path}?{q}")
    return http("POST", f"{API}/{path}", data=q.encode())

def put_file(path, raw, message):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    payload = {"message": message, "content": base64.b64encode(raw).decode()}
    try:
        with urllib.request.urlopen(urllib.request.Request(url + "?ref=main", headers=GH_HDR), timeout=30) as r:
            payload["sha"] = json.load(r)["sha"]
    except urllib.error.HTTPError:
        pass
    http("PUT", url, data=json.dumps(payload).encode(), headers=GH_HDR)

def kuliev(ref):
    for _ in range(3):
        try:
            with urllib.request.urlopen(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev", timeout=30) as r:
                d = json.load(r)["data"]
            if d.get("edition", {}).get("identifier") == "ru.kuliev":
                return d["text"].replace(" - ", " — ").strip()
        except Exception as e:
            print("alquran.cloud:", e)
            time.sleep(5)
    return None

def display_quote(q, full):
    """Фрагмент -> текст для карточки: многоточия там, где аят обрезан; внутренние кавычки «» -> „“."""
    i = full.find(q)
    s = q.strip()
    starts, ends = i == 0, i + len(q) >= len(full.rstrip())
    if not ends:
        s = s.rstrip(" ,;:—-")
        if s.endswith("."):
            s = s[:-1] + "…"
        elif not s.endswith(("!", "?", "»", "…")):
            s += "…"
    elif s.endswith((",", ";", ":", "-", "—")):
        s = s.rstrip(" ,;:—-") + "…"
    if not starts or s[:1].islower():
        s = "…" + s.lstrip("…")
    out, depth = [], 0
    for ch in s:
        if ch == "«":
            depth += 1; out.append("„")
        elif ch == "»":
            if depth: depth -= 1; out.append("“")
        else:
            out.append(ch)
    s = "".join(out)
    if depth:
        s = s.replace("„", "", depth)
    if s.endswith("“."):
        s = s[:-1]
    return s

def category(hour):
    return "m" if 6 <= hour <= 11 else "d" if 12 <= hour <= 17 else "e" if 18 <= hour <= 20 else "n"

slot = os.environ.get("SLOT") or datetime.datetime.now(ZoneInfo("Asia/Almaty")).strftime("%Y-%m-%dT%H:00")
dry = slot.startswith("dry:")
slot = slot[4:] if dry else slot
hour = int(slot[11:13])
subprocess.run([sys.executable, "ig.py"], env=dict(os.environ, SLOT=("dry:" if dry else "") + slot))
schedule = json.load(open("schedule.json", encoding="utf-8"))
post = schedule.get(slot)
used = json.load(open("used.json", encoding="utf-8")) if os.path.exists("used.json") else {}
bank_ref = None
if slot in used.values() and not dry:
    print(f"{slot} уже опубликован"); sys.exit(0)

if not post:
    bank = json.load(open("bank.json", encoding="utf-8"))
    cat = category(hour)
    queue = [b for b in bank if b["ref"] not in used and b["t"] == cat] + \
            [b for b in bank if b["ref"] not in used and b["t"] != cat]
    for b in queue:
        full = kuliev(b["ref"])
        if not full:
            sys.exit("Не удалось получить перевод Кулиева — пропускаю час, ничего не публикую")
        q = b.get("q") or full
        if q not in full or len(q) > 260:
            print(f"ПРОПУСК {b['ref']}: фрагмент не совпал с переводом Кулиева")
            used[b["ref"]] = "skip"
            continue
        post = {"quote": display_quote(q, full), "source": f"Коран, {b['ref']}", "explain": b["x"]}
        bank_ref = b["ref"]
        break
    if not post:
        print("Банк аятов закончился — нужно пополнить bank.json"); sys.exit(0)

if post.get("image"):
    image_path = post["image"]
else:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
    from render import render
    img = render(post["quote"], post["source"], post.get("explain", ""), hour)
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=90)
    image_path = f"cards/{slot.replace(':', '-')}.jpg"
    put_file(image_path, buf.getvalue(), f"card {image_path}")
    time.sleep(5)

image_url = f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(image_path)}"
print("QUOTE:", post.get("quote", ""))
if dry:
    print("DRY", image_url)
    sys.exit(0)
text = post.get("text") or post.get("explain", "")
user_id = threads("GET", "me", fields="id")["id"]
container = threads("POST", f"{user_id}/threads", media_type="IMAGE", image_url=image_url, text=text)
time.sleep(30)
result = threads("POST", f"{user_id}/threads_publish", creation_id=container["id"])
print(f"Опубликовано {slot}: {image_path} -> {result}")
used[bank_ref or f"slot {slot}"] = slot
put_file("used.json", json.dumps(used, ensure_ascii=False, indent=1).encode(), f"used {slot}")
