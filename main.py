import requests
import pandas as pd
import time
from datetime import datetime

# ==============================
# KONFIGIRASYON - CHANJE SA YO
# ==============================
OANDA_API_KEY = "METE_API_KEY_OU_ICI"
OANDA_ACCOUNT_ID = "001-001-21518859-001"
TELEGRAM_TOKEN = "METE_TOKEN_OU_ICI"
CHAT_ID = "METE_CHAT_ID_OU_ICI"

# OANDA API URLs (Demo)
OANDA_URL = "https://api-fxtrade.oanda.com/v3"

PAIRS = [
    "EUR_USD", "GBP_USD", "USD_JPY",
    "AUD_USD", "NZD_USD", "USD_CAD"
]

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json"
}

# ==============================
# TELEGRAM
# ==============================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erè Telegram: {e}")

# ==============================
# JWENN DONE OANDA
# ==============================
def get_candles(pair, count=50):
    url = f"{OANDA_URL}/instruments/{pair}/candles"
    params = {
        "count": count,
        "granularity": "M15",
        "price": "M"
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params)
        data = r.json()
        candles = data.get("candles", [])
        
        closes = []
        for c in candles:
            if c["complete"]:
                closes.append(float(c["mid"]["c"]))
        
        return closes
    except Exception as e:
        print(f"Erè OANDA {pair}: {e}")
        return []

# ==============================
# KALKILE RSI
# ==============================
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

# ==============================
# KALKILE EMA
# ==============================
def calc_ema(closes, period):
    if len(closes) < period:
        return []
    
    k = 2 / (period + 1)
    ema = [sum(closes[:period]) / period]
    
    for price in closes[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    
    return ema

# ==============================
# JWENN SIYAL
# ==============================
def get_signal(pair):
    closes = get_candles(pair, count=50)
    
    if len(closes) < 30:
        return None
    
    ema9 = calc_ema(closes, 9)
    ema21 = calc_ema(closes, 21)
    rsi = calc_rsi(closes)
    
    if not ema9 or not ema21 or not rsi:
        return None
    
    curr_ema9 = ema9[-1]
    curr_ema21 = ema21[-1]
    prev_ema9 = ema9[-2]
    prev_ema21 = ema21[-2]
    curr_price = closes[-1]
    
    signal = None
    strength = ""
    
    # BUY signal
    if prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21:
        signal = "BUY"
        strength = "💪 STRONG" if rsi < 50 else "✅ NORMAL"
    
    # SELL signal
    elif prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21:
        signal = "SELL"
        strength = "💪 STRONG" if rsi > 50 else "✅ NORMAL"
    
    if signal:
        return {
            "pair": pair.replace("_", "/"),
            "signal": signal,
            "strength": strength,
            "price": round(curr_price, 5),
            "rsi": rsi,
            "time": datetime.utcnow().strftime("%H:%M:%S UTC")
        }
    
    return None

# ==============================
# FORMAT MESAJ
# ==============================
def format_message(s):
    emoji = "🟢" if s["signal"] == "BUY" else "🔴"
    msg = (
        f"📊 <b>FOREX SIGNAL</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💱 <b>Pè:</b> {s['pair']}\n"
        f"{emoji} <b>Siyal:</b> {s['signal']} {s['strength']}\n"
        f"💰 <b>Pri:</b> {s['price']}\n"
        f"📈 <b>RSI:</b> {s['rsi']}\n"
        f"🕐 <b>Lè:</b> {s['time']}\n"
        f"━━━━━━━━━━━━━━━\n"
        f"⚠️ <i>Toujou fè analiz pa ou anvan ou trade</i>"
    )
    return msg

# ==============================
# REZIME CHAK 15 SIYAL
# ==============================
results = []

def add_result(pair, signal, outcome):
    results.append({
        "pair": pair,
        "signal": signal,
        "outcome": outcome,
        "time": datetime.utcnow().strftime("%H:%M:%S")
    })
    
    if len(results) >= 15:
        send_summary()
        results.clear()

def send_summary():
    wins = sum(1 for r in results if r["outcome"] == "WIN")
    losses = len(results) - wins
    rate = round((wins / len(results)) * 100) if results else 0
    
    msg = "📋 <b>REZIME 15 DÈNYE SIYAL:</b>\n━━━━━━━━━━━━━━━\n"
    for r in results:
        icon = "✅" if r["outcome"] == "WIN" else "❌"
        msg += f"{r['pair']} {r['time']} {r['signal']} {icon}\n"
    
    msg += f"━━━━━━━━━━━━━━━\n"
    msg += f"✅ Wins: {wins} | ❌ Losses: {losses}\n"
    msg += f"🏆 Win Rate: {rate}%"
    
    send_telegram(msg)

# ==============================
# LOOP PRENSIPAL
# ==============================
def main():
    print("✅ Bot démarré!")
    send_telegram("🤖 <b>Forex Signal Bot démarré!</b>\nAp surveye mache a... 👀")
    
    last_signals = {}

    while True:
        print(f"\n🔍 {datetime.utcnow().strftime('%H:%M:%S')} - Ap verifye siyal yo...")
        
        for pair in PAIRS:
            result = get_signal(pair)
            
            if result:
                key = f"{result['pair']}_{result['signal']}"
                
                if last_signals.get(result['pair']) != key:
                    msg = format_message(result)
                    send_telegram(msg)
                    last_signals[result['pair']] = key
                    print(f"✅ Siyal: {result['pair']} {result['signal']}")
            
            time.sleep(2)
        
        print("⏳ Tann 15 minit...")
        time.sleep(900)

if __name__ == "__main__":
    main()
