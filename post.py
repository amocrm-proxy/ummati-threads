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
import kk                                          # kk.ON — казахский режим (аяты Алтая, хадисов нет)

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
VOICE = False                                     # ролики с голосом автора — пока не используем
if hour in (9, 12, 15, 18, 21) and not dry and yt_key not in used:   # Shorts/TikTok 5 раз в день (+ Reels в 12, 18 и 21)
    try:
        # по кругу аят → хадис → поддержка (сквозной счёт роликов с 15/10/2026), ролик с ковриками — ежедневно в 21:00;
        # аят в 09 и 18 — отрывок Корана по порядку, в остальное время — «Сильный аят»
        n = (datetime.date.fromisoformat(slot[:10]) - datetime.date(2026, 10, 15)).days * 5 + (9, 12, 15, 18, 21).index(hour)
        kind = ["ayah", "hadith", "support"][n % 3]                   # сура/аят → хадис → поддержка
        wd = datetime.date.fromisoformat(slot[:10]).weekday()
        if hour == 21:                                               # ролик с ковриками — каждый день в 21:00
            kind = "sale"
        if kind == "ayah":
            kind = "auto" if hour in (9, 18) else "card"
        if kk.ON and kind == "hadith":                               # казахский режим: вместо хадиса — «Сильный аят»
            kind = "card"
        spec, vref = f"{kind}:{slot[:13]}", None
        if hour == 18 and VOICE:                      # в 18:00 — ролик с голосом автора, если он записан (пока выключено)
            try:
                import tg
                vref = tg.next_voice()
            except BaseException as e:
                print("Telegram:", e)
            if vref:
                spec = f"voice:{vref}"
        YOUTUBE = True                                # Алафаси убран (Content ID), чтецы: Хусари / Айюб / Абдуль-Басит
        inputs = {"spec": spec, "youtube": "true" if YOUTUBE or spec.startswith("voice") else "false", "reels": "true", "tiktok": "true", "threads": "true"}
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
# тест форматов: 12 часов в сутки — картинка, 12 — чистый текст (пары часов: 0–1 картинка, 2–3 текст, 4–5 картинка…)
TEXT_HOUR = (hour // 2) % 2 == 1
plain = None                                      # текст для текстового поста (≤ 500 знаков), иначе — картинка
ready = None                                      # готовые картинки (рубрика «Аят и наука»)
import science as S
sci = S.entry(slot) if hour == S.HOUR and not post and not kk.ON else None   # «Аят и наука» пока только на русском
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
elif hour % 3 == 0:                               # аят → хадис → слова поддержки по кругу: 0, 3, 6… — аят Корана по порядку
    n = int(used.get("q_next", 1))
    got = C.ayah_cards((n - 1) % C.TOTAL_AYAHS + 1)
    if not got:
        sys.exit("Не удалось получить перевод Кулиева — пропускаю час, ничего не публикую")
    cards, text, ref = got
    pointer = ("q_next", n + 1)
    print("Аят", n, ref)
    if TEXT_HOUR:                                 # текстовый пост: аят целиком, дословно, если влезает
        a = C.ayah((n - 1) % C.TOTAL_AYAHS + 1)
        if a and kk.ON:
            plain = f"«{a[2]}»\n\n{kk.caption(a[0], a[1])}"
        elif a:
            plain = f"«{a[2]}»\n\nКоран, сура «{C.NAMES[a[0] - 1]}», аят {a[1]}. Перевод смыслов Э. Кулиева."
elif hour % 3 == 1 and kk.ON:                     # казахский режим: вместо хадиса — аят из подборки bank.json
    bank = [b["ref"] for b in json.load(open("bank.json", encoding="utf-8")) if not b.get("q")]
    k = int(used.get("kb_next", 0))
    s_, a_ = kk.parse_ref(bank[k % len(bank)]); t_ = kk.text(s_, a_)
    parts = C.chunks(t_)
    cards = [(C.show(p, i, len(parts)), kk.ref(s_, a_) + (f" · {i + 1}/{len(parts)}" if len(parts) > 1 else ""),
              f"{kk.sura(s_)}. {kk.SOURCE}", kk.K_QURAN) for i, p in enumerate(parts)]
    text = kk.caption(s_, a_) + "\n\n" + kk.TAGS + " #аят"
    pointer = ("kb_next", k + 1)
    if TEXT_HOUR:
        plain = f"«{t_}»\n\n{kk.caption(s_, a_)}"
    print("Аят (подборка)", k, s_, a_)
elif hour % 3 == 1:                               # 1, 4, 7… — следующий хадис
    H = C.hadiths()
    k = int(used.get("h_next", 0))
    h = H[k % len(H)]
    cards, text = C.hadith_cards(h)
    pointer = ("h_next", k + 1)
    if TEXT_HOUR:                                 # текстовый пост: ближайший хадис, который целиком влезает в 490 знаков
        for j in range(k, k + 40):
            hj = H[j % len(H)]
            intro, body = C.hadith_parts(hj)
            attr = hj.get("attr", ""); attr = attr[:1].upper() + attr[1:]
            t = (intro + "\n\n" if intro else "") + (f"«{body}»" if intro else body) + \
                f"\n\n{attr}. {hj.get('grade') or 'Хадис'}."
            if len(t) <= 490:
                plain, pointer = t, ("h_next", j + 1)
                print("Хадис текстом", j, hj["id"]); break
    print("Хадис", k, h["id"])
else:                                             # 2, 5, 8… — «Слова поддержки» (аяты и хадисы утешения, дословно)
    import support as SP
    k = int(used.get("s_next", 0))
    x = SP.item(k)
    if not x:
        sys.exit("Не удалось получить текст для «Слов поддержки» — пропускаю час")
    cards, text = SP.cards(x)
    pointer = ("s_next", k + 1)
    if TEXT_HOUR:
        plain = SP.plain(x)
    print("Поддержка", k, x[0])

if plain and len(plain) > 490:                    # длинный аят/хадис — Threads не пустит, публикуем картинкой
    print("Текст длиннее 490 знаков — публикую картинкой"); plain = None
if plain:
    paths, cards = [], [(plain[:60], "", "", "ТЕКСТ")]
elif post and post.get("image"):
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
    print("DRY", urls, "\n", plain or text)
    sys.exit(0)
user_id = threads("GET", "me", fields="id")["id"]
if plain:
    container = threads("POST", f"{user_id}/threads", media_type="TEXT", text=plain)
elif len(urls) == 1:
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
