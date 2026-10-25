"""Ключ Threads с автопродлением. Ключ живёт 60 дней — post.py раз в неделю продлевает его
(graph.threads.net/refresh_access_token) и кладёт новый в th_token.enc (зашифрован, пароль — секрет TG_TOKEN).
Если в секретах GitHub поставить новый THREADS_TOKEN вручную — он сразу заменит сохранённый."""
import hashlib, json, os, subprocess, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "th_token.enc")

def _crypt(data, decrypt=False):
    args = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-a", "-A", "-pass", "env:TG_TOKEN"]
    if decrypt:
        args.insert(3, "-d")
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout

def _base():
    return hashlib.sha256(os.environ["THREADS_TOKEN"].strip().encode()).hexdigest()[:16]

def get():
    env = os.environ["THREADS_TOKEN"].strip()
    if os.path.exists(STORE) and os.environ.get("TG_TOKEN"):
        try:
            d = json.loads(_crypt(open(STORE, "rb").read(), decrypt=True))
            if d.get("base") == _base():
                return d["token"]
        except Exception as e:
            print("Threads ключ: сохранённый не прочитался —", e)
    return env

def refresh(put_file):
    """Продлить ключ на 60 дней и сохранить. Возвращает новый ключ (сам ключ не печатаем)."""
    q = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": get()})
    with urllib.request.urlopen(f"https://graph.threads.net/refresh_access_token?{q}", timeout=30) as r:
        d = json.load(r)
    new = d["access_token"]
    if os.environ.get("TG_TOKEN"):
        put_file("th_token.enc", _crypt(json.dumps({"base": _base(), "token": new}).encode()), "th_token")
    print("Threads ключ продлён, действует ещё", int(d.get("expires_in", 0)) // 86400, "дн.")
    return new
