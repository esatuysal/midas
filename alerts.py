import os
import sys
import json
import datetime as dt
import urllib.parse
import urllib.request
import yfinance as yf

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT = os.environ.get("TELEGRAM_CHAT_ID")
NTFY = os.environ.get("NTFY_TOPIC")
STATE = "alerts_state.json"
NOW = dt.datetime.now(dt.timezone.utc)

# ad, sembol, haber filtresi anahtar kelimeleri
ASSETS = {
    "gold": ("Altın", "GC=F", ["altın", "ons"]),
    "sp": ("S&P 500", "^GSPC", ["s&p", "wall street", "fed"]),
    "ndx": ("Nasdaq-100", "^NDX", ["nasdaq", "wall street", "fed"]),
}
# kural -> tekrar bildirim bekleme süresi (saat)
COOLDOWN = {"dip": 24, "oversold": 24, "hot": 72, "cross": 24}


def send(text):
    if NTFY:
        try:
            urllib.request.urlopen(urllib.request.Request(
                f"https://ntfy.sh/{NTFY}", data=text.encode("utf-8"),
                headers={"Priority": "high"}), timeout=20)
            return True
        except Exception as e:
            print("ntfy gönderim hatası:", type(e).__name__)
            return False
    if not TOKEN or not CHAT:
        print("Telegram bilgileri (secret) tanımlı değil.")
        return False
    data = urllib.parse.urlencode(
        {"chat_id": CHAT, "text": text, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=data), timeout=20)
        return True
    except Exception as e:
        print("Telegram gönderim hatası:", type(e).__name__)
        return False


def rsi(c, n=14):
    d = c.diff().dropna()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return float(100 - 100 / (1 + (up / dn).iloc[-1]))


if "--test" in sys.argv:
    ok = send("✅ Bot çalışıyor. Altın, S&P 500 ve Nasdaq-100 için kurallar her 15 dakikada kontrol edilir.")
    sys.exit(0 if ok else 1)

try:
    state = json.load(open(STATE, encoding="utf-8"))
except Exception:
    state = {}
try:
    news = json.load(open("data.json", encoding="utf-8")).get("news", [])
except Exception:
    news = []

fired, lines = [], []
for k, (name, sym, kw) in ASSETS.items():
    try:
        c = yf.Ticker(sym).history(period="1y")["Close"].dropna()
        p, r = float(c.iloc[-1]), rsi(c)
        sma200 = float(c.tail(200).mean()) if len(c) >= 200 else None
        gold = k == "gold"
        hi = float(c.tail(30).max()) if gold else float(c.max())
        dd = (1 - p / hi) * 100
        rules = {
            "dip": (dd >= (5 if gold else 10),
                    f"{name} {'30 günlük' if gold else '52 haftalık'} zirveden %{dd:.1f} düştü: alım bölgesi"),
            "oversold": (r < 30, f"{name} RSI {r:.0f}: aşırı satım bölgesi"),
            "hot": (r > 70, f"{name} RSI {r:.0f}: aşırı alım, ek alım için acele etme"),
            "cross": (bool(sma200) and p < sma200 and float(c.iloc[-2]) >= sma200,
                      f"{name} 200 günlük ortalamanın altına indi"),
        }
    except Exception as e:
        print(k, "veri hatası:", type(e).__name__)
        continue
    for rule, (cond, msg) in rules.items():
        key = f"{k}:{rule}"
        if not cond:
            state.pop(key, None)
            continue
        last = state.get(key)
        if last and (NOW - dt.datetime.fromisoformat(last)).total_seconds() < COOLDOWN[rule] * 3600:
            continue
        fired.append(key)
        extra = [n for n in news if any(w in n["title"].lower() for w in kw)][:2]
        txt = f"{'🟡' if gold else '🔵'} {msg}\nFiyat {p:,.2f} · RSI {r:.0f}"
        for n in extra:
            txt += f"\n• {n['title']}\n  {n['link']}"
        lines.append(txt)

if lines:
    msg = "\n\n".join(lines) + "\n\nKural tetiklendi, yatırım tavsiyesi değildir."
    if send(msg):
        for key in fired:
            state[key] = NOW.isoformat()

with open(STATE, "w", encoding="utf-8") as f:
    json.dump(state, f)
