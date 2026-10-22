"""Автопостинг ummati в Instagram. Запускается из post.py каждый час.
1) Если в ig_schedule.json есть публикации на этот час — публикует их (готовые картинки).
2) Иначе сам собирает и рисует публикацию по плану дня:
   08 — сторис: следующий аят Корана по порядку, 14 — сторис: следующий хадис (hadiths.json),
   17 — сторис «Слова поддержки» (support.json: аяты и хадисы утешения),
   12 — карусель «Аят и наука» (science.py), 19 — карусель (через день: аят / польза или товар), 21 — сторис-акция с фото.
   Все банки идут по кругу. SLOT=dry:... — нарисовать и загрузить без публикации."""
import json, os, sys, io, time, datetime, subprocess, urllib.request, urllib.parse, urllib.error, base64
from zoneinfo import ZoneInfo
import kk                                        # kk.ON — казахский режим

G = "https://graph.facebook.com/v21.0"
IG_USER = "17841478246747969"
PAGE_ID = "1369084289619381"
TOKEN = os.environ.get("IG_TOKEN", "")
REPO = os.environ["GITHUB_REPOSITORY"]
GH_HDR = {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}", "Accept": "application/vnd.github+json"}
START = datetime.date(2026, 10, 16)
SHOP = True                                      # Ummati Family — только продажи (аяты/сунна/әдеп — в Instagram уағыз)

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
PENDING = {}                                     # указатели (аят/хадис), которые двигаем только после публикации

def auto_item(slot, used):
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pillow"], check=True)
    import ig_render as R
    C = json.load(open("ig_content_kk.json" if kk.ON else "ig_content.json", encoding="utf-8"))
    DM = kk.WRITE_DM if kk.ON else "Пишите в директ"
    P = ""
    h = int(slot[11:13]); d = (datetime.date.fromisoformat(slot[:10]) - START).days
    tags = "\n\n" + C["tags"]
    off = C["offer"]
    def offer(page=None):
        return R.text_slide("choc", off["kicker"], title=off["title"], body=off["body"], page=page, footer=DM)
    if SHOP and h in (8, 12, 14, 17, 19):        # Ummati Family — магазин: сторис 08/14/17, карусель 19 (shop/); пятница — жұма
        sys.path.insert(0, "shop")
        import shop
        day = datetime.date.fromisoformat(slot[:10])
        if day.weekday() == 4 and h in (8, 12, 17):
            return "stories", [shop.friday_story(h, R)], ""
        if h == 12:
            return None
        if h == 19:
            ims, cap = shop.carousel(day, d)
            return "carousel", ims, cap
        return "stories", [shop.story(day, d * 3 + (8, 14, 17).index(h), R, DM)], ""
    if h == 8:                                   # аяты Корана по порядку (перевод Кулиева, длинный аят — несколько сторис)
        import content
        n = int(used.get("igq_next", 1))
        got = content.ayah_cards((n - 1) % content.TOTAL_AYAHS + 1)
        if not got: return None
        PENDING["igq_next"] = n + 1
        if kk.ON:
            return "stories", [R.text_slide("cream", "Құран Кәрім", quote=q, source=src, body=ex, story=True)
                               for q, src, ex, kick in got[0]], ""
        return "stories", [R.text_slide("cream" if kick == "СЛОВА ВСЕВЫШНЕГО" else "emer",
                                        "Слова Всевышнего" if kick == "СЛОВА ВСЕВЫШНЕГО" else "Смысл аята",
                                        quote=q, source=src, body=ex, story=True)
                           for q, src, ex, kick in got[0]], ""
    if h == 14 and kk.ON:                        # казахский режим: вместо хадиса — аят из подборки (с конца bank.json)
        import content
        bank = [b["ref"] for b in json.load(open("bank.json", encoding="utf-8")) if not b.get("q")][::-1]
        k = int(used.get("igk_next", 0)); s, a = kk.parse_ref(bank[k % len(bank)]); t = kk.text(s, a)
        parts = content.chunks(t)
        PENDING["igk_next"] = k + 1
        return "stories", [R.text_slide("emer", "Құран Кәрім", quote=content.show(p, i, len(parts)),
                                        source=kk.ref(s, a), body=f"{kk.sura(s)}. {kk.SOURCE}", story=True)
                           for i, p in enumerate(parts)], ""
    if h == 14:                                  # хадисы по порядку из hadiths.json
        import content
        H = content.hadiths(); k = int(used.get("igh_next", 0))
        cards, _ = content.hadith_cards(H[k % len(H)])
        PENDING["igh_next"] = k + 1
        return "stories", [R.text_slide("emer", "Хадис", quote=q, source=src, body=ex, story=True)
                           for q, src, ex, _ in cards], ""
    if h == 17:                                  # «Слова поддержки» — аяты и хадисы утешения (support.json), дословно
        import support
        k = int(used.get("igs_next", 0))
        x = support.item(k)
        if not x: return None
        PENDING["igs_next"] = k + 1
        cards, _ = support.cards(x)
        return "stories", [R.text_slide("emer", "Жүрекке демеу" if kk.ON else "Слова поддержки", quote=q, source=src, body=ex, story=True)
                           for q, src, ex, _ in cards], ""
    if h == 12 and kk.ON:                        # «Аят и наука» пока только на русском
        return None
    if h == 12:                                  # «Аят и наука» — карусель (science.json по кругу)
        import science
        e = science.entry(slot)
        got = science.build(e) if e else None
        if not got: return None
        return "carousel", got[0], got[1]
    if h == 21:
        ph, t, b = C["promos"][d % len(C["promos"])]
        return "story", [R.photo_slide(P + ph, t, b, story=True, footer=DM, kicker="ummati")], ""
    if h == 19:
        if d % 2 == 0 and not kk.ON:             # «Мысль дня» — русский текст, в казахском режиме только карусели
            a = next_ayah(used)
            if not a: return None
            q, src, x = a
            ims = [R.text_slide("cream", "Слова Всевышнего", quote=q, source=src, page="1/3"),
                   R.text_slide("cream", "Мысль дня", title=x, page="2/3"),
                   R.text_slide("emer", "ummati", title="Сохраните и отправьте тому, кому это нужно сегодня", page="3/3")]
            return "carousel", ims, f"«{q}» ({src}, пер. Э. Кулиева).\n\n{x}" + tags
        car = C["carousels"][(d if kk.ON else d // 2) % len(C["carousels"])]
        n = len(car["slides"]); ims = []
        for i, s in enumerate(car["slides"], 1):
            pg = f"{i}/{n}"
            if s[0] == "photo":
                ims.append(R.photo_slide(P + s[1], s[2], s[3] or None, page=pg, kicker="ummati" if i == 1 else None))
            elif s[0] == "text":
                ims.append(R.text_slide(s[1], s[2], title=s[3], body=s[4], page=pg,
                                        footer=DM if i == n else None))
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
    if int(slot[11:13]) not in (8, 12, 14, 17, 19, 21):
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
        if kind == "stories":
            for p in paths:
                print("IG сторис:", slot, publish({"type": "story", "images": [p]}, tok))
        else:
            print("IG опубликовано:", slot, publish({"type": kind, "images": paths, "caption": caption}, tok))
        for k, v in list(used.items()):
            if v == "?": used[k] = slot
        used.update(PENDING)
        used[key] = slot; save_used(used, key)
    except Exception as e:
        print("IG ОШИБКА", slot, e)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("IG ОШИБКА:", e)
