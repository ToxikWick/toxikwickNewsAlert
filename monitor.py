import os
import time
import hashlib
import threading
import requests

from flask import Flask

app = Flask(__name__)

# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1247262258")

# Public Forex Factory calendar JSON feed commonly used
# for calendar data.
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

CHECK_INTERVAL = 30  # seconds

seen_events = set()


# ============================================================
# SIMPLE WEB SERVER
# Render Free Web Service needs an HTTP server.
# ============================================================

@app.route("/")
def home():
    return "ToxikWick Forex News Alert is running."


@app.route("/health")
def health():
    return "OK"


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):
    if not BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is missing.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        print("Telegram:", response.status_code, response.text)

        return response.ok

    except Exception as e:
        print("Telegram error:", e)
        return False


# ============================================================
# IMPACT
# ============================================================

def is_high_impact(event):
    impact = str(event.get("impact", "")).lower()

    return (
        impact == "high"
        or impact == "red"
        or "high" in impact
    )


# ============================================================
# CURRENCY BIAS
# ============================================================

def currency_bias(event):
    """
    Estimate whether the released number is bullish,
    bearish or neutral for the affected currency.

    This is deliberately conservative.
    """

    actual = event.get("actual")
    forecast = event.get("forecast")

    if actual in (None, "", "null"):
        return "⚪ NEUTRAL", "No actual result yet."

    if forecast in (None, "", "null"):
        return "⚪ NEUTRAL", "No forecast available."

    try:
        a = float(str(actual).replace("%", "").replace(",", "").strip())
        f = float(str(forecast).replace("%", "").replace(",", "").strip())
    except Exception:
        return "⚪ NEUTRAL", "Result requires interpretation."

    name = str(event.get("title", "")).lower()

    # Events where a HIGHER reading is normally positive
    higher_is_better = [
        "employment",
        "nonfarm",
        "nfp",
        "retail sales",
        "gdp",
        "industrial production",
        "manufacturing pmi",
        "services pmi",
        "composite pmi",
        "consumer confidence",
        "business confidence",
        "consumer sentiment",
        "average hourly earnings",
        "wage",
        "durable goods",
        "housing starts",
        "building permits"
    ]

    # Events where a LOWER reading is normally positive
    lower_is_better = [
        "unemployment",
        "jobless claims",
        "initial jobless claims",
        "continuing jobless claims"
    ]

    # Inflation is more complicated because central-bank
    # reaction matters. Treat it separately.
    inflation_events = [
        "cpi",
        "core cpi",
        "ppi",
        "core pce",
        "pce price",
        "inflation"
    ]

    if any(x in name for x in inflation_events):
        if a > f:
            return (
                "🟢 BULLISH",
                "Inflation is hotter than forecast; this can support a more hawkish central-bank outlook."
            )
        elif a < f:
            return (
                "🔴 BEARISH",
                "Inflation is softer than forecast; this can support a less hawkish central-bank outlook."
            )

    if any(x in name for x in lower_is_better):
        if a < f:
            return (
                "🟢 BULLISH",
                "The result is better than forecast."
            )
        elif a > f:
            return (
                "🔴 BEARISH",
                "The result is worse than forecast."
            )

    if any(x in name for x in higher_is_better):
        if a > f:
            return (
                "🟢 BULLISH",
                "The result is better than forecast."
            )
        elif a < f:
            return (
                "🔴 BEARISH",
                "The result is worse than forecast."
            )

    return "⚪ NEUTRAL", "Actual and forecast do not produce a simple directional interpretation."


# ============================================================
# PAIR DIRECTION
# ============================================================

def pair_implication(currency, bias):
    """
    Gives examples of how the currency bias could translate
    into common FX pairs.
    """

    currency = str(currency).upper()

    bullish_pairs = {
        "USD": "Potential BUY USD pairs such as USD/JPY; potential SELL EUR/USD, GBP/USD.",
        "EUR": "Potential BUY EUR/USD or EUR/GBP.",
        "GBP": "Potential BUY GBP/USD or GBP/JPY.",
        "JPY": "Potential BUY JPY pairs such as USD/JPY SELL; interpretation depends on quote direction.",
        "AUD": "Potential BUY AUD/USD or AUD/JPY.",
        "NZD": "Potential BUY NZD/USD or NZD/JPY.",
        "CAD": "Potential BUY CAD/JPY; potential SELL USD/CAD.",
        "CHF": "Potential BUY CHF/JPY; potential SELL USD/CHF."
    }

    bearish_pairs = {
        "USD": "Potential SELL USD pairs such as USD/JPY; potential BUY EUR/USD, GBP/USD.",
        "EUR": "Potential SELL EUR/USD or EUR/GBP.",
        "GBP": "Potential SELL GBP/USD or GBP/JPY.",
        "JPY": "Potential SELL JPY pairs such as USD/JPY BUY; interpretation depends on quote direction.",
        "AUD": "Potential SELL AUD/USD or AUD/JPY.",
        "NZD": "Potential SELL NZD/USD or NZD/JPY.",
        "CAD": "Potential SELL CAD/JPY; potential BUY USD/CAD.",
        "CHF": "Potential SELL CHF/JPY; potential BUY USD/CHF."
    }

    if "BULLISH" in bias:
        return bullish_pairs.get(currency, "Check the specific pair's quote direction.")

    if "BEARISH" in bias:
        return bearish_pairs.get(currency, "Check the specific pair's quote direction.")

    return "No directional pair bias."


# ============================================================
# EVENT ID
# ============================================================

def event_id(event):
    raw = "|".join([
        str(event.get("date", "")),
        str(event.get("title", "")),
        str(event.get("country", "")),
        str(event.get("currency", "")),
        str(event.get("impact", ""))
    ])

    return hashlib.sha256(raw.encode()).hexdigest()


# ============================================================
# FORMAT ALERT
# ============================================================

def format_alert(event, unexpected=False):

    currency = event.get("country") or event.get("currency") or "UNKNOWN"
    title = event.get("title", "Unknown event")

    actual = event.get("actual", "—")
    forecast = event.get("forecast", "—")
    previous = event.get("previous", "—")

    bias, explanation = currency_bias(event)

    pair_direction = pair_implication(currency, bias)

    tag = "🚨 NEW / UNEXPECTED RED NEWS" if unexpected else "🔴 HIGH IMPACT NEWS"

    message = f"""
<b>{tag}</b>

💱 <b>Currency:</b> {currency}
📰 <b>Event:</b> {title}

📊 <b>Actual:</b> {actual}
🎯 <b>Forecast:</b> {forecast}
📚 <b>Previous:</b> {previous}

<b>Currency Bias:</b> {bias}

💡 {explanation}

📈 <b>Possible FX implication:</b>
{pair_direction}

⚠️ <b>Important:</b> This is a news interpretation, not a guaranteed BUY/SELL signal. Wait for price action confirmation before entering.
"""

    return message.strip()


# ============================================================
# DOWNLOAD CALENDAR
# ============================================================

def get_calendar():

    try:
        response = requests.get(
            CALENDAR_URL,
            timeout=20,
            headers={
                "User-Agent": "ToxikWick-NewsMonitor/1.0"
            }
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:
        print("Calendar error:", e)
        return []


# ============================================================
# MONITOR
# ============================================================

def monitor():

    global seen_events

    print("===================================")
    print("ToxikWick Forex News Alert")
    print("Monitor started")
    print("Checking every", CHECK_INTERVAL, "seconds")
    print("===================================")

    # Test Telegram connection
    send_telegram(
        "🟢 <b>ToxikWick News Alert</b>\n\n"
        "Monitor is online and ready to detect high-impact red-folder news."
    )

    while True:

        events = get_calendar()

        if not isinstance(events, list):
            print("Unexpected calendar format.")
            time.sleep(CHECK_INTERVAL)
            continue

        for event in events:

            if not isinstance(event, dict):
                continue

            if not is_high_impact(event):
                continue

            eid = event_id(event)

            # New event
            if eid not in seen_events:

                seen_events.add(eid)

                message = format_alert(
                    event,
                    unexpected=True
                )

                print(message)

                send_telegram(message)

        # Prevent unlimited memory growth
        if len(seen_events) > 5000:
            seen_events = set(list(seen_events)[-2500:])

        time.sleep(CHECK_INTERVAL)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    worker = threading.Thread(
        target=monitor,
        daemon=True
    )

    worker.start()

    # Render provides PORT automatically.
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
  )
