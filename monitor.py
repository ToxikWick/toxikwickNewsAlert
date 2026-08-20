import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

# =========================
# ENVIRONMENT VARIABLES
# =========================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
PARSE_API_KEY = os.environ.get("PARSE_API_KEY")

# =========================
# PARSE / FOREX FACTORY API
# =========================

API_URL = (
    "https://api.parse.bot/scraper/"
    "0d3aa2e2-80b6-42dc-986a-d7f0845f4deb/"
    "get_news_latest"
)

# Check once every 60 seconds
CHECK_INTERVAL = 60

# Stories already processed
seen_stories = set()


# =========================
# WEB SERVER
# =========================

@app.route("/")
def home():
    return "ToxikWick Forex Factory News Monitor is running."


# =========================
# TELEGRAM
# =========================

def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            },
            timeout=15
        )

        print(
            "TELEGRAM STATUS:",
            response.status_code,
            flush=True
        )

    except Exception as e:

        print(
            "TELEGRAM ERROR:",
            repr(e),
            flush=True
        )


# =========================
# GET FOREX FACTORY NEWS
# =========================

def get_news():

    if not PARSE_API_KEY:

        print(
            "❌ PARSE_API_KEY IS MISSING",
            flush=True
        )

        return None

    try:

        response = requests.get(
            API_URL,
            headers={
                "X-API-Key": PARSE_API_KEY
            },
            timeout=30
        )

        print(
            "PARSE API STATUS:",
            response.status_code,
            flush=True
        )

        response.raise_for_status()

        return response.json()

    except Exception as e:

        print(
            "❌ PARSE API ERROR:",
            repr(e),
            flush=True
        )

        return None


# =========================
# EXTRACT STORIES
# =========================

def extract_stories(data):

    if not isinstance(data, dict):
        return []

    stories = data.get("data", [])

    if isinstance(stories, dict):

        stories = stories.get(
            "stories",
            []
        )

    if not isinstance(stories, list):

        stories = data.get(
            "stories",
            []
        )

    if not isinstance(stories, list):

        return []

    return stories


# =========================
# UNEXPECTED HIGH-IMPACT FILTER
# =========================

def is_unexpected_high_impact(story):

    impact = str(
        story.get("impact", "")
    ).strip().lower()

    # Only HIGH / RED news
    if impact not in (
        "high",
        "red",
        "high impact",
        "high-impact"
    ):

        return False

    headline = str(
        story.get("headline", "")
    ).lower()

    # Scheduled releases that we DON'T want
    scheduled = [

        "minutes of the federal open market committee",
        "fomc minutes",
        "consumer price index",
        "cpi",
        "nonfarm payroll",
        "non-farm payroll",
        "employment report",
        "unemployment rate",
        "retail sales",
        "gross domestic product",
        "gdp",
        "producer price index",
        "ppi",
        "interest rate decision",
        "rate decision",
        "monetary policy statement",
        "central bank minutes",
        "meeting minutes",
        "jobless claims",
        "durable goods orders",
        "industrial production",
        "housing starts",
        "existing home sales",
        "new home sales"
    ]

    for term in scheduled:

        if term in headline:

            return False

    # Strong breaking-news words
    breaking = [

        "announce",
        "announcement",
        "announces",
        "unexpected",
        "emergency",
        "surprise",
        "breaking",
        "tariff",
        "sanction",
        "sanctions",
        "intervention",
        "suspends",
        "suspended",
        "halts",
        "halted",
        "imposes",
        "imposed",
        "effective immediately",
        "emergency meeting"
    ]

    for term in breaking:

        if term in headline:

            return True

    # Institutions that can produce unexpected
    # market-moving announcements

    institutions = [

        "treasury",
        "federal reserve",
        "fed",
        "ecb",
        "bank of england",
        "boe",
        "bank of japan",
        "boj",
        "bank of canada",
        "boc",
        "swiss national bank",
        "snb",
        "reserve bank of australia",
        "rba",
        "reserve bank of new zealand",
        "rbnz",
        "white house",
        "u.s. government",
        "us government",
        "government"
    ]

    for institution in institutions:

        if institution in headline:

            return True

    return False


# =========================
# MONITOR
# =========================

def monitor():

    global seen_stories

    print(
        "===================================",
        flush=True
    )

    print(
        "TOXIKWICK FOREX FACTORY MONITOR",
        flush=True
    )

    print(
        "UNEXPECTED HIGH-IMPACT NEWS ONLY",
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

                if not isinstance(
                    story,
                    dict
                ):

                    continue

                headline = str(
                    story.get(
                        "headline",
                        ""
                    )
                )

                url = str(
                    story.get(
                        "url",
                        ""
                    )
                )

                preview = str(
                    story.get(
                        "preview",
                        ""
                    )
                )

                impact = str(
                    story.get(
                        "impact",
                        ""
                    )
                )

                print(
                    "STORY:",
                    headline,
                    "| IMPACT:",
                    impact,
                    flush=True
                )

                if not headline or not url:

                    continue

                # Only unexpected high-impact stories
                if not is_unexpected_high_impact(
                    story
                ):

                    continue

                story_id = url

                # First scan creates baseline.
                # Old stories are NOT sent to Telegram.

                if first_scan:

                    seen_stories.add(
                        story_id
                    )

                    continue

                # Ignore duplicates

                if story_id in seen_stories:

                    continue

                # New qualifying story

                seen_stories.add(
                    story_id
                )

                print(
                    "🚨 NEW HIGH-IMPACT BREAKING NEWS:",
                    headline,
                    flush=True
                )

                message = (
                    "🚨 <b>TOXIKWICK BREAKING NEWS</b>\n\n"
                    f"📰 <b>{headline}</b>\n\n"
                    f"🔴 <b>Impact:</b> HIGH\n\n"
                )

                if preview:

                    # Keep Telegram message manageable
                    short_preview = preview[:700]

                    message += (
                        f"📝 {short_preview}\n\n"
                    )

                message += (
                    f"🔗 {url}\n\n"
                    "⚠️ Unexpected high-impact news. "
                    "Check price action before trading."
                )

                send_telegram(
                    message
                )

        first_scan = False

        time.sleep(
            CHECK_INTERVAL
        )


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":

    worker = threading.Thread(
        target=monitor,
        daemon=True
    )

    worker.start()

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
                    )
