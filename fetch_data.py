import json
import datetime as dt
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import yfinance as yf

T = {
    "gold": ("Altın (ons, $)", "GC=F"),
    "sp": ("S&P 500", "^GSPC"),
    "ndx": ("Nasdaq-100", "^NDX"),
    "usdtry": ("USD/TRY", "USDTRY=X"),
}
Q = ["Fed faiz kararı", "altın ons fiyatı", "S&P 500 Nasdaq", "dolar TL kur", "Wall Street"]

out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "items": {}, "news": []}

for key, (name, sym) in T.items():
    try:
        h = yf.Ticker(sym).history(period="1y")["Close"].dropna()
        out["items"][key] = {
            "name": name,
            "price": round(float(h.iloc[-1]), 2),
            "chg": round(float(h.iloc[-1] / h.iloc[-2] - 1) * 100, 2),
            "high30": round(float(h.tail(30).max()), 2),
            "high52": round(float(h.max()), 2),
        }
    except Exception as e:
        print(key, "hata:", e)

seen = set()
news = []
for q in Q:
    try:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
            {"q": q + " when:2d", "hl": "tr", "gl": "TR", "ceid": "TR:tr"})
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        root = ET.fromstring(urllib.request.urlopen(req, timeout=20).read())
        for it in list(root.iter("item"))[:5]:
            title = (it.findtext("title") or "").strip()
            if not title or title in seen:
                continue
            seen.add(title)
            src = it.find("source")
            news.append({
                "title": title,
                "link": it.findtext("link"),
                "source": src.text if src is not None else "",
                "date": parsedate_to_datetime(it.findtext("pubDate")).isoformat(),
            })
    except Exception as e:
        print(q, "haber hata:", e)

news.sort(key=lambda n: n["date"], reverse=True)
out["news"] = news[:12]

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
