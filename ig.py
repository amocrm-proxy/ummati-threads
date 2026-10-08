"""Автопостинг ummati в Instagram. Запускается из post.py каждый час.
1) Если в ig_schedule.json есть публикации на этот час — публикует их (готовые картинки).
2) Иначе сам собирает и рисует публикацию по плану дня:
   08 — сторис с аятом (банк bank.json, сверка с Кулиевым), 14 — сторис-факт,
   19 — карусель (через день: аят / польза или товар), 21 — сторис-акция с фото.
   Все банки идут по кругу. SLOT=dry:... — нарисовать и загрузить без публикации."""
import json, os, sys, io, time, datetime, subprocess, urllib.request, urllib.parse, urllib.error, base64
from zoneinfo import ZoneInfo

G = "https://graph.facebook.com/v21.0"
IG_USER = "17841478246747969"
PAGE_ID = "1369084289619381"
TOKEN = os.environ.get("IG_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
GH_HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}
START = datetime.date(2026, 10, 16)

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
    print("Токен:", info.get("type"), "| истекает:", "никогда" if not exp else datetime.datetime.fromtimestamp(exp).strftime("%d/%m/%Y"))
    if info.get("type") == "PAGE":
        return TOKEN
    for p in call("GET", "me/accounts", fields="id,access_token", access_token=TOKEN).get("data", []):
        if p["id"] == PAGE_ID:
            print("ВНИМАНИЕ: в IG_TOKEN токен пользователя, а не Страницы — он истечёт.")
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
    return f"https://raw.githubusercontent.com/{REPO}/main/{urllib.parse.quote(path)}"

def publish(item, tok):
    imgs = item["images"]
    if item["type"] == "story":
        cid = call("POST", f"{IG_USER}/media", media_type="STORIES", image_url=url(imgs[0]), access_token=tok)["id"]
    elif len(imgs) == 1:
        cid = call("POST", f"{IG_USER}/media", image_url=url(imgs[0]), caption=item.get("caption", ""), access_token=tok)["id"]
    else:
        kids = [call("POST", f"{IG_USER}/media", image_url=url(im), is_carousel_item="true", access_token=tok)["id"] for im in imgs]
        for k in kids:
            wait_ready(k, tok)
        cid = call("POST", f"{IG_USER}/media", media_type="CAROUSEL", children=",".join(kids),
                   caption=item.get("caption", ""), access_token=tok)["id"]
    wait_ready(cid, tok)
    return call("POST", f"{IG_USER}/media_publish", creation_id=cid, access_token=tok)

def put_file(path, raw, msg):
    api = f"https://api.github.com/repos/{REPO}/contents/{path}"
    body = {"message": msg, "content": base64.b64encode(raw).decode()}
    try:
        with urllib.request.urlopen(urllib.request.Request(api + "?ref=main", headers=GH_HDR), timeout=30) as r:
            body["sha"] = json.load(r)["sha"]
    except urllib.error.HTTPError:
        pass
    urllib.request.urlopen(urllib.request.Request(api, data=json.dumps(body).encode(), method="PUT", headers=GH_HDR), timeout=60)

def save_used(used, msg):
    raw = json.dumps(used, ensure_ascii=False, indent=1).encode()
    open("used.json", "wb").write(raw)
    put_file("used.json", raw, msg)

# ---------- аяты (как в post.py) ----------
def kuliev(ref):
    for _ in range(3):
        try:
            with urllib.request.urlopen(f"https://api.alquran.cloud/v1/ayah/{ref}/ru.kuliev", timeout=30) as r:
                d = json.load(r)["data"]
            if d.get("edition", {}).get("identifier") == "ru.kuliev":
                return d["text"].replace(" - ", " — ").strip()
        except Exception as e:
            print("alquran.cloud:", e); time.sleep(5)
    return None

def display_quote(q, full):
    i = full.find(q); s = q.strip()
    starts, ends = i == 0, i + len(q) >= len(full.rstrip())
    if not ends:
        s = s.rstrip(" ,;:—-")
        if s.endswith("."): s = s[:-1] + "…"
        elif not s.endswith(("!", "?", "»", "…")): s += "…"
    elif s.endswith((",", ";", ":", "-", "—")):
        s = s.rstrip(" ,;:—-") + "…"
    if not starts or s[:1].islower():
        s = "…" + s.lstrip("…")
    out, depth = [], 0
    for ch in s:
        if ch == "«": depth += 1; out.append("„")
        elif ch == "»":
            if depth: depth -= 1; out.append("“")
        else: out.append(ch)
    s = "".join(out)
    if depth: s = s.replace("„", "", depth)
    if s.endswith("“."): s = s[:-1]
    return s

def next_ayah(used):
    bank = json.load(open("bank.json", encoding="utf-8"))[::-1]   # с конца, чтобы не совпадать с Threads
    for _ in range(2):
        for b in bank:
            if f"igq {b['ref']}" in used or len(b["x"]) < 45 or b["x"].startswith("…"):
                continue
            full = kuliev(b["ref"])
            if not full:
                return None
            q = b.get("q") or full
            if q not in full or len(q) > 260:
                used[f"igq {b['ref']}"] = "skip"; continue
            used[f"igq {b['ref']}"] = "?"
            return display_quote(q, full), f"Коран, {b['ref']}", b["x"]
        for k in [k for k in used if k.startswith("igq ")]:   # банк закончился — по кругу
            del used[k]
    return None

# ---------- автогенерация ----------
def auto_item(slot, used):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
    import ig_render as R
    C = json.load(open("ig_content.json", encoding="utf-8"))
    P = "photos/"
    h = int(slot[11:13]); d = (datetime.date.fromisoformat(slot[:10]) - START).days
    tags = "\n\n" + C["tags"]
    off = C["offer"]
    def offer(page=None):
        return R.text_slide("choc", off["kicker"], title=off["title"], body=off["body"], page=page, footer="Пишите в директ")
    if h == 8:
        a = next_ayah(used)
        if not a: return None
        return "story", [R.text_slide("cream", "Слова Всевышнего", quote=a[0], source=a[1], body=a[2], story=True)], ""
    if h == 14:
        t, b = C["facts"][d % len(C["facts"])]
        return "story", [R.text_slide("emer", "Знаете ли вы?", title=t, body=b, story=True)], ""
    if h == 21:
        ph, t, b = C["promos"][d % len(C["promos"])]
        return "story", [R.photo_slide(P + ph, t, b, story=True, footer="Пишите в директ", kicker="ummati")], ""
    if h == 19:
        if d % 2 == 0:
            a = next_ayah(used)
            if not a: return None
            q, src, x = a
            ims = [R.text_slide("cream", "Слова Всевышнего", quote=q, source=src, page="1/3"),
                   R.text_slide("cream", "Мысль дня", title=x, page="2/3"),
                   R.text_slide("emer", "ummati", title="Сохраните и отправьте тому, кому это нужно сегодня", page="3/3")]
            return "carousel", ims, f"«{q}» ({src}, пер. Э. Кулиева).\n\n{x}" + tags
        car = C["carousels"][(d // 2) % len(C["carousels"])]
        n = len(car["slides"]); ims = []
        for i, s in enumerate(car["slides"], 1):
            pg = f"{i}/{n}"
            if s[0] == "photo":
                ims.append(R.photo_slide(P + s[1], s[2], s[3] or None, page=pg, kicker="ummati" if i == 1 else None))
            elif s[0] == "text":
                ims.append(R.text_slide(s[1], s[2], title=s[3], body=s[4], page=pg,
                                        footer="Пишите в директ" if i == n else None))
            else:
                ims.append(offer(pg))
        return "carousel", ims, car["caption"] + tags
    return None

def main():
    if not TOKEN:
        print("IG_TOKEN не задан"); return
    slot = os.environ.get("SLOT") or datetime.datetime.now(ZoneInfo("Asia/Almaty")).strftime("%Y-%m-%dT%H:00")
    dry = slot.startswith("dry:")
    slot = slot[4:] if dry else slot
    tok = page_token()
    sched = json.load(open("ig_schedule.json", encoding="utf-8")) if os.path.exists("ig_schedule.json") else {}
    used = json.load(open("used.json", encoding="utf-8")) if os.path.exists("used.json") else {}
    hour = slot[:13]
    planned = sorted(k for k in sched if k[:13] == hour)
    if planned:
        for key in planned:
            if f"ig {key}" in used:
                print("IG уже опубликовано:", key); continue
            if dry:
                print("IG DRY (готовое):", key, sched[key]["images"]); continue
            try:
                print("IG опубликовано:", key, publish(sched[key], tok))
                used[f"ig {key}"] = slot; save_used(used, f"ig {key}")
            except Exception as e:
                print("IG ОШИБКА", key, e)
        return
    if int(slot[11:13]) not in (8, 14, 19, 21):
        return
    key = f"ig auto {slot}"
    if key in used and not dry:
        print("IG уже опубликовано:", slot); return
    item = auto_item(slot, used)
    if not item:
        print("IG: на этот час ничего нет"); return
    kind, ims, caption = item
    paths = []
    for i, im in enumerate(ims, 1):
        buf = io.BytesIO(); im.save(buf, "JPEG", quality=88)
        p = f"igauto/{slot.replace(':', '-')}_{i}.jpg"
        put_file(p, buf.getvalue(), f"ig card {p}"); paths.append(p)
    time.sleep(5)
    if dry:
        print("IG DRY:", kind, [url(p) for p in paths], "\n", caption); return
    try:
        print("IG опубликовано:", slot, publish({"type": kind, "images": paths, "caption": caption}, tok))
        for k, v in list(used.items()):
            if v == "?": used[k] = slot
        used[key] = slot; save_used(used, key)
    except Exception as e:
        print("IG ОШИБКА", slot, e)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("IG ОШИБКА:", e)
