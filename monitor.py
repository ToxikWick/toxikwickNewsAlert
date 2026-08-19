import os
import requests
from flask import Flask

app = Flask(__name__)

PARSE_API_KEY = os.environ.get("PARSE_API_KEY")

API_URL = (
    "https://api.parse.bot/scraper/"
    "0d3aa2e2-80b6-42dc-986a-d7f0845f4deb/"
    "get_news_latest"
)


@app.route("/")
def home():
    return "ToxikWick API diagnostic is running."


@app.route("/test")
def test_api():

    if not PARSE_API_KEY:
        return "PARSE_API_KEY is missing", 500

    try:

        response = requests.get(
            API_URL,
            headers={
                "X-API-Key": PARSE_API_KEY
            },
            timeout=30
        )

        print(
            "PARSE STATUS:",
            response.status_code,
            flush=True
        )

        print(
            "PARSE RESPONSE:",
            response.text[:5000],
            flush=True
        )

        return (
            f"Status: {response.status_code}<br><br>"
            f"{response.text[:5000]}"
        )

    except Exception as e:

        print(
            "PARSE ERROR:",
            repr(e),
            flush=True
        )

        return f"Error: {e}", 500


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
