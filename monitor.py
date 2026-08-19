import os
import time
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask

app = Flask(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1247262258")

NEWS_URL = "https://www.forexfactory.com/news"

CHECK_INTERVAL = 30

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

        print("TELEGRAM:", r.status_code, flush=True)

    except Exception as e:
        print("TELEGRAM ERROR:", repr(e), flush=True)


def get_news():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/139.0 Safari/537.36"
        )
    }

    try:

        r = requests.get(
            NEWS_URL,
            headers=headers,
            timeout=20
        )

        print(
            "FOREX FACTORY STATUS:",
            r.status_code,
            flush=True
        )

        r.raise_for_status()

        return r.text

    except Exception as e:

        print(
            "FOREX FACTORY ERROR:",
            repr(e),
            flush=True
        )

        return None


def find_high_impact_stories(html):

    soup = BeautifulSoup(html, "html.parser")

    stories = []

    # Find links pointing to Forex Factory news articles.
    for link in soup.find_all("a", href=True):

        href = link.get("href", "")

        if "/news/" not in href:
            continue

        title = link.get_text(" ", strip=True)

        if not title:
            continue

        # Find the nearest surrounding story container.
        parent = link

        for _ in range(6):

            if parent.parent:
                parent = parent.parent

            text = parent.get_text(" ", strip=True)

            # Forex Factory marks these stories as:
            # "High Impact Breaking"
            if "High Impact Breaking" in text:

                if href.startswith("/"):
                    url = "https://www.forexfactory.com" + href
                else:
                    url = href

                stories.append({
                    "title": title,
                    "url": url
                })

                break

    # Remove duplicates
    unique = {}

    for story in stories:
        unique[story["url"]] = story

    return list(unique.values())


def make_alert(story):

    return f"""
🚨 <b>HIGH IMPACT BREAKING NEWS</b>

📰 <b>{story['title']}</b>

🌐 <b>Source:</b> Forex Factory

🔗 {story['url']}

⚠️ <b>NEW HIGH-IMPACT BREAKING STORY</b>

Check the headline before entering any trade.
"""


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
        "HIGH IMPACT BREAKING NEWS ONLY",
        flush=True
    )

    print(
        "Checking every",
        CHECK_INTERVAL,
        "seconds",
        flush=True
    )

    print(
        "===================================",
        flush=True
    )

    first_scan = True

    while True:

        html = get_news()

        if html:

            stories = find_high_impact_stories(html)

            print(
                "HIGH IMPACT STORIES FOUND:",
                len(stories),
                flush=True
            )

            for story in stories:

                story_id = story["url"]

                # First scan creates a baseline.
                # We DO NOT alert for old stories already on the page.
                if first_scan:

                    seen_stories.add(story_id)

                    continue

                # New story appeared after monitoring started.
                if story_id not in seen_stories:

                    seen_stories.add(story_id)

                    print(
                        "🚨 NEW HIGH IMPACT STORY:",
                        story["title"],
                        flush=True
                    )

                    send_telegram(
                        make_alert(story)
                    )

        first_scan = False

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
