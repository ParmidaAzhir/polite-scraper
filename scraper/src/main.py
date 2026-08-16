from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
import json
import time

import requests
from bs4 import BeautifulSoup


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/ParmidaAzhir/polite-scraper)"
}

TIMEOUT = 10
DELAY = 0.5


def utc_now():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def fetch_page(url, cache_path):
    cache_path = Path(cache_path)

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")

        fetched_at = datetime.fromtimestamp(
            cache_path.stat().st_mtime,
            tz=timezone.utc
        ).isoformat(timespec="seconds").replace("+00:00", "Z")

        print(f"CACHE HIT: {cache_path.name}")
        return html, fetched_at

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

    response.encoding = "utf-8"
    html = response.text

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")

    print(f"response_size={len(html.encode('utf-8'))} bytes")

    return html, utc_now()


def discover_books():
    current_url = START_URL
    catalogue_pages = 0
    discovered_books = []

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        cache_path = (
            Path("cache")
            / f"catalogue-page-{catalogue_pages}.html"
        )

        html, _ = fetch_page(current_url, cache_path)

        soup = BeautifulSoup(html, "html.parser")

        books = soup.select("article.product_pod h3 a")

        for book in books:
            product_url = urljoin(
                current_url,
                book["href"]
            )

            discovered_books.append({
                "product_url": product_url,
                "source_page": current_url,
            })

        next_link = soup.select_one("li.next a")

        if next_link:
            current_url = urljoin(
                current_url,
                next_link["href"]
            )
        else:
            current_url = None

    unique_books = {}

    for book in discovered_books:
        unique_books[book["product_url"]] = book

    books = list(unique_books.values())

    print()
    print(f"catalogue_pages={catalogue_pages}")
    print(f"discovered={len(discovered_books)}")
    print(f"unique_urls={len(books)}")
    print()

    return books


def extract_book(book):
    product_url = book["product_url"]
    source_page = book["source_page"]

    path = urlparse(product_url).path
    book_slug = Path(path).parent.name

    cache_path = (
        Path("cache")
        / "books"
        / f"{book_slug}.html"
    )

    html, fetched_at = fetch_page(
        product_url,
        cache_path
    )

    soup = BeautifulSoup(html, "html.parser")

    product = soup.select_one("div.product_main")

    title = product.select_one("h1").get_text(strip=True)

    price_text = product.select_one(
        "p.price_color"
    ).get_text(strip=True)

    availability = product.select_one(
        "p.instock.availability"
    )

    availability_text = " ".join(
        availability.stripped_strings
    )

    rating = product.select_one("p.star-rating")

    rating_text = None

    for class_name in rating.get("class", []):
        if class_name != "star-rating":
            rating_text = class_name

    description_element = soup.select_one(
        "#product_description + p"
    )

    if description_element:
        description = description_element.get_text(
            strip=True
        )
    else:
        description = None

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def main():
    books = discover_books()

    raw_records = []

    for book in books:
        record = extract_book(book)
        raw_records.append(record)

    print(json.dumps(
        raw_records[0],
        indent=2,
        ensure_ascii=False
    ))

    print()
    print(f"detail_pages={len(raw_records)}")


if __name__ == "__main__":
    main()