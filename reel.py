"""Публикует готовый ролик (videos/....mp4 + .json) в Instagram как Reels.
python reel.py videos/auto_2026-10-11T18.mp4"""
import json, os, sys, time
import ig

def main(path):
    m = json.load(open(path.rsplit(".", 1)[0] + ".json", encoding="utf-8"))
    name = "igauto/reel_" + os.path.basename(path)
    ig.put_file(name, open(path, "rb").read(), f"reel {name}")
    time.sleep(10)
    tok = ig.page_token()
    caption = m["description"].replace("#shorts", "#reels").replace("Instagram: @ummati.family", "Пишите в директ")
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
