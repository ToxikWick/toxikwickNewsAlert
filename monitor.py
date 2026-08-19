import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1247262258")

CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

CHECK_INTERVAL = 30


@app.route("/")
def home():
    return "ToxikWick Forex News Alert"


def telegram_test():
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN is missing")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": "🟢 ToxikWick monitor diagnostic test is working."
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        print("TELEGRAM STATUS:", response.status_code)

        if response.ok:
            print("✅ Telegram connection successful")
        else:
            print("❌ Telegram connection failed:", response.text)

    except Exception as e:
        print("❌ Telegram connection error:", e)


def check_calendar():

    print("\n==============================")
    print("CHECKING NEWS CALENDAR")
    print("==============================")

    try:

        response = requests.get(
            CALENDAR_URL,
            headers={
                "User-Agent": "Mozilla/5.0 ToxikWickNewsAlert"
            },
            timeout=20
        )

        print("CALENDAR HTTP STATUS:", response.status_code)

        response.raise_for_status()

        events = response.json()

        print("TOTAL EVENTS RECEIVED:", len(events))

        high_impact = []

        for event in events:

            if not isinstance(event, dict):
                continue

            impact = str(event.get("impact", "")).lower()

            if impact in ("high", "red") or "high" in impact:

                high_impact.append(event)

        print("HIGH IMPACT EVENTS:", len(high_impact))

        for event in high_impact[:10]:

            print(
                "🔴",
                event.get("country"),
                "|",
                event.get("title"),
                "|",
                event.get("date")
            )

        if not high_impact:
            print("⚠️ No high-impact events found in current response.")

        print("==============================\n")

    except Exception as e:

        print("❌ CALENDAR ERROR:", repr(e))


def monitor():

    print("===================================")
    print("TOXIKWICK FOREX NEWS ALERT")
    print("DIAGNOSTIC MONITOR STARTED")
    print("Checking every", CHECK_INTERVAL, "seconds")
    print("===================================")

    telegram_test()

    while True:

        check_calendar()

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":

    worker = threading.Thread(
        target=monitor,
        daemon=True
    )

    worker.start()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
