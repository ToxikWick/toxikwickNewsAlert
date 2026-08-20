import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PARSE_API_KEY = os.environ["PARSE_API_KEY"]

API_URL = (
    "https://api.parse.bot/scraper/"
    "0d3aa2e2-80b6-42dc-986a-d7f0845f4deb/"
    "get_news_latest"
)

# 5 requests/minute is the API limit.
# We use 60 seconds between checks.
CHECK_INTERVAL = 60

seen_stories = set()


@app.route("/")
def home():
    return "ToxikWick Forex Factory News Monitor is running."


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        r = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            },
            timeout=15
        )

        print("TELEGRAM STATUS:", r.status_code, flush=True)

    except Exception as e:
        print("TELEGRAM ERROR:", repr(e), flush=True)


def get_news():

    try:
        r = requests.get(
            API_URL,
            headers={
                "X-API-Key": PARSE_API_KEY
            },
            timeout=30
        )

        print("PARSE API STATUS:", r.status_code, flush=True)

        r.raise_for_status()

        data = r.json()

        return data

    except Exception as e:
        print("PARSE API ERROR:", repr(e), flush=True)
        return None


def extract_stories(data):

    if not isinstance(data, dict):
        return []

    # Handle the API's data wrapper.
    stories = data.get("data", [])

    if isinstance(stories, dict):
        stories = stories.get("stories", [])

    if not isinstance(stories, list):
        stories = data.get("stories", [])

    if not isinstance(stories, list):
        return []

    return stories


def is_high_impact(story):

    impact = str(
        story.get("impact", "")
    ).strip().lower()

    return impact in (
        "high",
        "red",
        "high impact",
        "high-impact"
    )


def monitor():

    global seen_stories

    print(
        "===================================",
        flush=True
    )

    print(
        "TOXIKWICK FOREX FACTORY NEWS MONITOR",
        flush=True
    )

    print(
        "HIGH IMPACT BREAKING NEWS ONLY",
        flush=True
    )

    print(
        "Checking every 60 seconds",
        flush=True
    )

    print(
        "===================================",
        flush=True
    )

    first_scan = True

    while True:

        data = get_news()

        if data is not None:

            stories = extract_stories(data)

            print(
                "NEWS STORIES RECEIVED:",
                len(stories),
                flush=True
            )

            for story in stories:

                if not isinstance(story, dict):
                    continue

                headline = story.get("headline", "")
                url = story.get("url", "")
                preview = story.get("preview", "")
                impact = story.get("impact", "")

                if not headline or not url:
                    continue

                if not is_high_impact(story):
                    continue

                story_id = url

                # First scan = establish baseline.
                # Do NOT alert for old stories.
                if first_scan:

                    seen_stories.add(story_id)

                    continue

                # NEW high-impact story.
                if story_id not in seen_stories:

                    seen_stories.add(story_id)

                    print(
                        "🚨 NEW HIGH-IMPACT STORY:",
                        headline,
                        flush=True
                    )

                    message = (
                        "🚨 <b>NEW HIGH-IMPACT "
                        "BREAKING NEWS</b>\n\n"
                        f"📰 <b>{headline}</b>\n\n"
                        f"🔴 <b>Impact:</b> {impact}\n\n"
                    )

                    if preview:
                        message += (
                            f"📝 {preview}\n\n"
                        )

                    message += (
                        f"🔗 {url}\n\n"
                        "⚠️ Check price action before "
                        "entering a trade."
                    )

                    send_telegram(message)

        first_scan = False

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":

    worker = threading.Thread(
        target=monitor,
        daemon=True
    )

    worker.start()

    port = int(
        os.environ.get("PORT", "10000")
    )

    app.run(
        host="0.0.0.0",
        port=port
                    )
