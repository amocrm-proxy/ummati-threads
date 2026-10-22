"""Магазин Ummati Family: карусели и сторис из фото shop/photos (catalog.json: поворот фото, тексты).
Вызывается из ig.py: 08/14/17 — сторис, 19 — карусель. Фото всегда ставятся ровно (поворот из catalog.json)."""
import datetime, json, os
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CAT = json.load(open(os.path.join(HERE, "catalog.json"), encoding="utf-8"))
PROMO_END = datetime.date(2026, 10, 31)
KIT = "🎁 Жиынтықта: жайнамаз, Зәмзәм суы, агат тасбих, сыйлық қаптамасы (zip-пакет + картон сөмке)"
TAGS = "#жайнамаз #намазныековрики #ummati #сыйлық #алматы #қазақстан"

def price(day):
    if day <= PROMO_END:
        return f"🔥 {PROMO_END.day} қазанға дейін: 1+1 — 2 жиынтық 9 900 ₸"
    return "💳 Жиынтық бағасы: 9 900 ₸"

def upright(name):
    """Фото ровно: поворот из catalog.json, сохраняем во временный файл (для photo_slide)."""
    im = Image.open(os.path.join(HERE, "photos", name + ".jpg")).convert("RGB")
    r = CAT["rotate"].get(name, 0)
    if r:
        im = im.rotate(r, expand=True)
    return im

def crop(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    l, t = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((l, t, l + w, t + h))

def carousel(day, n):
    c = CAT["carousels"][n % len(CAT["carousels"])]
    ims = [crop(upright(p), 1080, 1350) for p in c["photos"]]
    caption = "\n".join([c["text"], "", "📏 110×70 см · жұмсақ барқыт · Anti Slip", KIT, price(day),
                         "🚚 Қазақстан бойынша — пошта немесе InDrive. Алматы ішінде 20:00-ден кейін — тегін",
                         "🤲 Әр сатып алудың 5%-ы қайырымдылыққа", "", "Тапсырыс: директке жазыңыз", "", TAGS])
    return ims, caption

def story(day, n, R, footer):
    st = CAT["stories"]
    s = st[n % len(st)]
    title, sub = s["title"], s["sub"]
    if title == "PROMO":
        title, sub = (("1+1 — 9 900 ₸", f"{PROMO_END.day} қазанға дейін: 2 жиынтық") if day <= PROMO_END
                      else ("Жиынтық — 9 900 ₸", "Жайнамаз, Зәмзәм суы, агат тасбих"))
    tmp = f"/tmp/shop_story_{n}.jpg"
    upright(s["photo"]).save(tmp, quality=95)
    return R.photo_slide(tmp, title, sub, story=True, footer=footer, kicker="ummati")
