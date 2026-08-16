from pathlib import Path

import requests


PAGE_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/ParmidaAzhir/polite-scraper)"
}

TIMEOUT = 10

CACHE_FILE = Path("cache/catalogue-page-1.html")


def get_catalogue_page():
    if CACHE_FILE.exists():
        html = CACHE_FILE.read_text(encoding="utf-8")

        print("CACHE HIT")
        print(f"response_size={len(html.encode('utf-8'))} bytes")

        return html

    print("FETCH")

    response = requests.get(
        PAGE_URL,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch page: HTTP {response.status_code}"
        )

    html = response.text

    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(html, encoding="utf-8")

    print(f"response_size={len(html.encode('utf-8'))} bytes")

    return html


if __name__ == "__main__":
    get_catalogue_page()