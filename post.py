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
    for attempt in range(4):                      # временные сбои (5xx, обрыв сети) — повторяем до 4 раз
        req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = f"Ошибка {method} {url.split('?')[0]} {e.code}: {e.read().decode()}"
            if e.code >= 500 and attempt < 3:
                print(msg, "— повтор через 30 с"); time.sleep(30); continue
        except (urllib.error.URLError, TimeoutError) as e:
            msg = f"Сеть {method} {url.split('?')[0]}: {e}"
            if attempt < 3:
                print(msg, "— повтор через 30 с"); time.sleep(30); continue
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
if not dry:                                       # Telegram-бот: забираем голосовые для рубрики «Размышление»
    try:
        import tg
        tg.run(put_file, datetime.datetime.now(ZoneInfo("Asia/Almaty")))
    except BaseException as e:
        print("Telegram:", e)
yt_key = f"yt {slot[:13]}"
if hour in (9, 12, 15, 18, 21) and not dry and yt_key not in used:   # YouTube Shorts 5 раз в день (+ Reels в 18:00)
    try:
        spec, vref = (f"card:{slot[:13]}" if hour in (12, 21) else f"auto:{slot[:13]}"), None   # 12 и 21 — «Сильный аят»
        if hour == 18:                                # в 18:00 — ролик с голосом автора, если он записан
            try:
                import tg
                vref = tg.next_voice()
            except BaseException as e:
                print("Telegram:", e)
            if vref:
                spec = f"voice:{vref}"
        inputs = {"spec": spec, "youtube": "true", "reels": "true" if hour == 18 else "false"}
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/actions/workflows/video.yml/dispatches", method="POST", headers=GH_HDR,
            data=json.dumps({"ref": "main", "inputs": inputs}).encode()), timeout=30)
        used[yt_key] = "yt"
        put_file("used.json", json.dumps(used, ensure_ascii=False, indent=1).encode(), yt_key)
        if vref:
            tg.mark_used(vref, put_file)
        print("YouTube Shorts: сборка запущена", inputs)
    except BaseException as e:
        print("YouTube Shorts: не удалось запустить:", e)
if slot in [v for k, v in used.items() if not k.startswith(("ig", "yt"))] and not dry:
    print(f"{slot} уже опубликован"); sys.exit(0)

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
from render import render
import content as C

pointer = None                                    # (ключ в used.json, новое значение) — двигаем только после публикации
ready = None                                      # готовые картинки (рубрика «Аят и наука»)
import science as S
sci = S.entry(slot) if hour == S.HOUR and not post else None
if sci:                                           # 12:00 — «Аят и наука» (та же карусель, что в Instagram)
    got = S.build(sci)
    if not got:
        sys.exit("Не удалось получить перевод Кулиева — пропускаю час, ничего не публикую")
    ready, _, text = got
    cards = [("Аят и наука", "", "", "")]
    print("Аят и наука:", sci["refs"])
elif post:                                          # ручной пост из schedule.json
    cards = [] if post.get("image") else [(post["quote"], post["source"], post.get("explain", ""), "СЛОВА ВСЕВЫШНЕГО")]
    text = post.get("text") or post.get("explain", "")
elif hour % 2 == 0:                               # чётный час — следующий аят Корана по порядку
    n = int(used.get("q_next", 1))
    got = C.ayah_cards((n - 1) % C.TOTAL_AYAHS + 1)
    if not got:
        sys.exit("Не удалось получить перевод Кулиева — пропускаю час, ничего не публикую")
    cards, text, ref = got
    pointer = ("q_next", n + 1)
    print("Аят", n, ref)
else:                                             # нечётный час — следующий хадис
    H = C.hadiths()
    k = int(used.get("h_next", 0))
    h = H[k % len(H)]
    cards, text = C.hadith_cards(h)
    pointer = ("h_next", k + 1)
    print("Хадис", k, h["id"])

if post and post.get("image"):
    paths = [post["image"]]
elif ready:
    paths = []
    for i, img in enumerate(ready, 1):
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=90)
        path = f"cards/{slot.replace(':', '-')}_{i}.jpg"
        put_file(path, buf.getvalue(), f"card {path}")
        paths.append(path)
    time.sleep(5)
else:
    paths = []
    for i, (q, src, ex, kicker) in enumerate(cards[:20], 1):
        img = render(q, src, ex, hour, kicker=kicker)
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=90)
        path = f"cards/{slot.replace(':', '-')}" + (f"_{i}" if len(cards) > 1 else "") + ".jpg"
        put_file(path, buf.getvalue(), f"card {path}")
        paths.append(path)
    time.sleep(5)

urls = [f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(p)}" for p in paths]
print("CARDS:", [c[0][:60] for c in cards])
if dry:
    print("DRY", urls, "\n", text)
    sys.exit(0)
user_id = threads("GET", "me", fields="id")["id"]
if len(urls) == 1:
    container = threads("POST", f"{user_id}/threads", media_type="IMAGE", image_url=urls[0], text=text)
else:
    kids = [threads("POST", f"{user_id}/threads", media_type="IMAGE", image_url=u, is_carousel_item="true")["id"] for u in urls]
    time.sleep(10)
    container = threads("POST", f"{user_id}/threads", media_type="CAROUSEL", children=",".join(kids), text=text)
time.sleep(30)
result = threads("POST", f"{user_id}/threads_publish", creation_id=container["id"])
print(f"Опубликовано {slot}: {paths} -> {result}")
used[f"slot {slot}"] = slot
if pointer:
    used[pointer[0]] = pointer[1]
put_file("used.json", json.dumps(used, ensure_ascii=False, indent=1).encode(), f"used {slot}")
