"""Собирает hadiths.json из «Энциклопедии переведённых хадисов» (hadeethenc.com), русский перевод.
Берём только бесспорные темы: Коран (1), достоинства дел и этикет (5), жизнеописание Пророка (7),
и только хадисы со степенью «достоверный» или «хороший». Порядок перемешан, но стабилен."""
import json, random, time, urllib.request

API = "https://hadeethenc.com/api/v1"

def get(url):
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print("повтор:", url, e); time.sleep(3 * (i + 1))
    raise RuntimeError(url)

ids = []
for cat in (1, 5, 7):
    page = 1
    while True:
        d = get(f"{API}/hadeeths/list/?language=ru&category_id={cat}&page={page}&per_page=100")
        ids += [h["id"] for h in d["data"] if h["id"] not in ids]
        if page >= int(d["meta"]["last_page"]):
            break
        page += 1
print("всего id:", len(ids))
out, grades = [], {}
for i in ids:
    h = get(f"{API}/hadeeths/one/?language=ru&id={i}")
    g = (h.get("grade") or "").strip()
    grades[g] = grades.get(g, 0) + 1
    if not any(w in g.lower() for w in ("достовер", "хорош")):
        continue
    text = (h.get("hadeeth") or "").strip()
    if not text or len(text) > 1500:
        continue
    out.append({"id": i, "text": text, "intro": (h.get("hadeeth_intro") or "").strip(),
                "attr": (h.get("attribution") or "").strip().rstrip("."), "grade": g.rstrip(".")})
    time.sleep(0.2)
print("степени:", json.dumps(grades, ensure_ascii=False))
random.Random(7).shuffle(out)
json.dump(out, open("hadiths.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("в банке хадисов:", len(out))
