from pydantic import BaseModel, Field, HttpUrl, ValidationError
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import time
import sys

import requests
from bs4 import BeautifulSoup


START_URL = "https://books.toscrape.com/catalogue/page-1.html"

HEADERS = {
    "User-Agent": "FlyRankInternship-A9/1.0 (+https://github.com/ParmidaAzhir/polite-scraper)"
}

TIMEOUT = 10
DELAY = 0.5
RETRY_DELAY = 1

class BookRecord(BaseModel):
    title: str
    product_url: HttpUrl
    price_text: str
    price_gbp: float = Field(ge=0)
    availability_text: str
    rating_text: str
    description: str | None = None
    source_page: HttpUrl
    fetched_at: datetime

def utc_now():
    return datetime.now(timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")

def normalize_price(price_text):
    return float(
        price_text.replace("£", "").strip()
    )

def fetch_page(url, cache_path, stats):
    cache_path = Path(cache_path)

    if cache_path.exists():
        html = cache_path.read_text(encoding="utf-8")

        fetched_at = datetime.fromtimestamp(
            cache_path.stat().st_mtime,
            tz=timezone.utc
        ).isoformat(timespec="seconds").replace("+00:00", "Z")

        stats["cache_hits"] += 1

        print(f"CACHE HIT: {cache_path.name}")
        return html, fetched_at

    for attempt in range(2):
        try:
            print(f"FETCH: {url}")

            time.sleep(DELAY)

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=TIMEOUT,
            )

            if response.status_code == 200:
                response.encoding = "utf-8"
                html = response.text

                cache_path.parent.mkdir(
                    parents=True,
                    exist_ok=True
                )

                cache_path.write_text(
                    html,
                    encoding="utf-8"
                )

                stats["pages_fetched"] += 1

                print(
                    f"response_size="
                    f"{len(html.encode('utf-8'))} bytes"
                )

                return html, utc_now()

            if response.status_code in (403, 404):
                raise RuntimeError(
                    f"HTTP {response.status_code}: {url}"
                )

            if 500 <= response.status_code < 600:
                if attempt == 0:
                    print("Temporary server error — retrying once")
                    time.sleep(RETRY_DELAY)
                    continue

                raise RuntimeError(
                    f"HTTP {response.status_code}: {url}"
                )

            raise RuntimeError(
                f"HTTP {response.status_code}: {url}"
            )

        except requests.exceptions.Timeout:
            if attempt == 0:
                print("Timeout — retrying once")
                time.sleep(RETRY_DELAY)
                continue

            raise RuntimeError(
                f"Timeout fetching: {url}"
            )


def discover_books(stats):
    current_url = START_URL
    catalogue_pages = 0
    discovered_books = []

    while current_url and catalogue_pages < 3:
        catalogue_pages += 1

        cache_path = (
            Path("cache")
            / f"catalogue-page-{catalogue_pages}.html"
        )

        html, _ = fetch_page(
            current_url,
            cache_path,
            stats
        )

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


def extract_book(book, stats):
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
        cache_path,
        stats
    )

    soup = BeautifulSoup(html, "html.parser")

    product = soup.select_one("div.product_main")

    title = product.select_one("h1").get_text(strip=True)

    price_text = product.select_one(
        "p.price_color"
    ).get_text(strip=True)

    price_gbp = normalize_price(price_text)

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
        "price_gbp": price_gbp,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }

def validate_records(raw_records):
    valid_records = []
    errors = []

    for record in raw_records:
        try:
            validated = BookRecord.model_validate(record)

            valid_records.append(
                validated.model_dump(mode="json")
            )

        except ValidationError as error:
            errors.append({
                "record": record,
                "reason": error.errors(),
            })

    return valid_records, errors

def main(test_failure=False):
    start_time = utc_now()
    start_clock = time.perf_counter()

    stats = {
        "pages_fetched": 0,
        "cache_hits": 0,
    }

    books = discover_books(stats)
    # Deliberately broken URL for the Stage 5 failure test
    if test_failure:
        books.append({
            "product_url": (
                "https://books.toscrape.com/catalogue/"
                "this-book-does-not-exist-999999/index.html"
            ),
            "source_page": START_URL,
        })

    raw_records = []
    fetch_errors = []

    for book in books:
        try:
            record = extract_book(book, stats)
            raw_records.append(record)

        except Exception as error:
            print(
                f"SKIPPED: {book['product_url']} — {error}"
            )

            fetch_errors.append({
                "product_url": book["product_url"],
                "reason": str(error),
            })

    valid_records, validation_errors = validate_records(
        raw_records
    )

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    books_file = output_dir / "books.json"
    errors_file = output_dir / "errors.json"
    report_file = output_dir / "run-report.json"

    books_file.write_text(
        json.dumps(
            valid_records,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    all_errors = fetch_errors + validation_errors

    errors_file.write_text(
        json.dumps(
            all_errors,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    duration = time.perf_counter() - start_clock

    report = {
        "start_time": start_time,
        "duration_seconds": round(duration, 2),
        "pages_fetched": stats["pages_fetched"],
        "cache_hits": stats["cache_hits"],
        "valid_records": len(valid_records),
        "invalid_records": len(validation_errors),
        "failed_pages": len(fetch_errors),
    }

    report_file.write_text(
        json.dumps(
            report,
            indent=2
        ),
        encoding="utf-8"
    )

    print()
    print(f"valid_records={len(valid_records)}")
    print(f"invalid_records={len(validation_errors)}")
    print(f"failed_pages={len(fetch_errors)}")
    print(f"books_saved={len(valid_records)}")

if __name__ == "__main__":
    test_failure = "--test-failure" in sys.argv
    main(test_failure=test_failure)