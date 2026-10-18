"""Публикует готовый ролик (videos/....mp4 + .json) в Instagram как Reels.
python reel.py videos/auto_2026-10-11T18.mp4"""
import json, os, re, sys, time
import ig

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

def main(path):
    m = json.load(open(path.rsplit(".", 1)[0] + ".json", encoding="utf-8"))
    name = "igauto/reel_" + os.path.basename(path)
    ig.put_file(name, open(path, "rb").read(), f"reel {name}")
    time.sleep(10)
    tok = ig.page_token()
    caption = tags_only(m)
    extra = {}
    cov = path.rsplit(".", 1)[0] + "_cover.jpg"
    if os.path.exists(cov):                       # своя обложка Reels (для сетки профиля)
        cname = "igauto/cover_" + os.path.basename(cov)
        ig.put_file(cname, open(cov, "rb").read(), f"cover {cname}")
        time.sleep(5); extra["cover_url"] = ig.url(cname)
    try:
        cid = ig.call("POST", f"{ig.IG_USER}/media", media_type="REELS", video_url=ig.url(name),
                      caption=caption, share_to_feed="true", access_token=tok, **extra)["id"]
    except RuntimeError as e:
        if not extra: raise
        print("обложка не принята, публикую без неё:", e)
        cid = ig.call("POST", f"{ig.IG_USER}/media", media_type="REELS", video_url=ig.url(name),
                      caption=caption, share_to_feed="true", access_token=tok)["id"]
    for _ in range(60):                           # видео обрабатывается дольше картинки — ждём до 5 минут
        st = ig.call("GET", cid, fields="status_code", access_token=tok).get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            sys.exit(f"Reels: Instagram не принял видео ({cid})")
        time.sleep(5)
    else:
        sys.exit("Reels: видео не обработалось за 5 минут")
    print("Reels опубликован:", ig.call("POST", f"{ig.IG_USER}/media_publish", creation_id=cid, access_token=tok))

if __name__ == "__main__":
    main(sys.argv[1])
