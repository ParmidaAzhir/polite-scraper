from pathlib import Path
from urllib.parse import urljoin
import time

import requests
from bs4 import BeautifulSoup


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/ParmidaAzhir/polite-scraper)"
}

TIMEOUT = 10
DELAY = 0.5


def fetch_page(url, cache_file):
    cache_path = Path("cache") / cache_file

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")

        print(f"CACHE HIT: {cache_file}")
        print(f"response_size={len(html.encode('utf-8'))} bytes")

        return html

    print(f"FETCH: {url}")

    time.sleep(DELAY)

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Failed to fetch {url}: HTTP {response.status_code}"
        )

    html = response.text

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"response_size={len(html.encode('utf-8'))} bytes")

    return html


def discover_books():
    current_url = START_URL

    book_urls = []
    catalogue_pages = 0

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        cache_file = f"catalogue-page-{catalogue_pages}.html"

        html = fetch_page(current_url, cache_file)

        soup = BeautifulSoup(html, "html.parser")

        books = soup.select("article.product_pod h3 a")

        for book in books:
            relative_url = book["href"]
            absolute_url = urljoin(current_url, relative_url)

            book_urls.append(absolute_url)

        next_link = soup.select_one("li.next a")

        if next_link:
            current_url = urljoin(
                current_url,
                next_link["href"]
            )
        else:
            current_url = None

    unique_urls = list(dict.fromkeys(book_urls))

    print()
    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls


if __name__ == "__main__":
    discover_books()