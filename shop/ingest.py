"""Фото для магазина Ummati Family: берёт файлы из релиза shop-N (архивы .zip и отдельные фото),
уменьшает до 1440 px по длинной стороне, сохраняет JPG в shop/photos/. Видео кладёт в shop/videos/ (если до 90 МБ).
python shop/ingest.py <папка_с_файлами_релиза>"""
import os, sys, zipfile, shutil, re
from PIL import Image, ImageOps
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()                          # фото с iPhone (.heic)
except ImportError:
    pass

SRC = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT, VID = os.path.join(HERE, "photos"), os.path.join(HERE, "videos")
os.makedirs(OUT, exist_ok=True)
IMG = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp")
MOV = (".mp4", ".mov", ".m4v")

work = os.path.join(SRC, "_x")
os.makedirs(work, exist_ok=True)
for f in os.listdir(SRC):
    p = os.path.join(SRC, f)
    if f.lower().endswith(".zip"):
        with zipfile.ZipFile(p) as z:
            for m in z.infolist():
                n = m.filename
                if m.is_dir() or "__MACOSX" in n or os.path.basename(n).startswith("."):
                    continue
                z.extract(m, work)
    elif os.path.isfile(p):
        shutil.copy(p, work)

def slug(name):
    s = re.sub(r"[^\w\-]+", "_", os.path.splitext(name)[0].lower()).strip("_")
    return s or "photo"

done = skipped = 0
for root, _, files in os.walk(work):
    for f in sorted(files):
        p, ext = os.path.join(root, f), os.path.splitext(f)[1].lower()
        base = slug(f)
        if ext in IMG:
            dst = os.path.join(OUT, base + ".jpg")
            k = 2
            while os.path.exists(dst):
                dst = os.path.join(OUT, f"{base}_{k}.jpg"); k += 1
            try:
                im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                im.thumbnail((1440, 1440), Image.LANCZOS)
                im.save(dst, "JPEG", quality=88, optimize=True, progressive=True)
                done += 1
            except Exception as e:
                print("не открылось:", f, e); skipped += 1
        elif ext in MOV:
            if os.path.getsize(p) <= 90 * 1024 * 1024:
                os.makedirs(VID, exist_ok=True)
                shutil.copy(p, os.path.join(VID, base + ext))
            else:
                print("видео больше 90 МБ — осталось только в релизе:", f)
        else:
            print("пропущен (не фото/видео):", f); skipped += 1
print(f"Готово: фото {done}, пропущено {skipped}")
