import json
import datetime as dt
import yfinance as yf

T = {
    "gold": ("Altın (ons, $)", "GC=F"),
    "sp": ("S&P 500", "^GSPC"),
    "ndx": ("Nasdaq-100", "^NDX"),
    "usdtry": ("USD/TRY", "USDTRY=X"),
}

out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "items": {}}

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

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
