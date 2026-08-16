# Polite Scraper

A Python web scraping pipeline that collects book data from the first three catalogue pages of Books to Scrape, validates the records, stores clean JSON output, handles failures safely, and reports what happened during each run.

## Target Classification

* **Target:** Books to Scrape — https://books.toscrape.com/
* **Purpose:** Practice building a polite and reliable web scraping pipeline.
* **Scope:** Only the first 3 catalogue pages will be scraped, for a total of 60 books.
* **Data collected:** Book title, product URL, price, availability, rating, description, source page, and fetch time.
* **Why this is appropriate:** Books to Scrape is a fictional bookstore created specifically as a safe sandbox for learning and testing web scraping.
* **robots.txt:** No robots file found. The request to `https://books.toscrape.com/robots.txt` returned `404 Not Found`.

I will not reuse this code on another site without checking its rules and terms first.

## Tech Stack

* Python 3.10+
* Requests — HTTP requests
* Beautiful Soup — HTML parsing and extraction
* Pydantic — schema validation
* Python `json` module — JSON output

## Installation

Clone the repository and enter the scraper folder:

```bash
git clone https://github.com/ParmidaAzhir/polite-scraper.git
cd polite-scraper/scraper
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run

Run the scraper with:

```bash
python src/main.py
```

A successful run creates:

```text
output/
├── books.json
├── errors.json
└── run-report.json
```

The scraper processes exactly the first 3 catalogue pages and discovers 60 unique books.

## Failure Test

A deliberate broken URL can be added with:

```bash
python src/main.py --test-failure
```

The fake page returns `404`, but the scraper continues running and keeps all 60 valid book records.

## Record Schema

Each validated book record contains:

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "price_gbp": 51.77,
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-16T07:26:09Z"
}
```

Pydantic validates every record before it is stored. Invalid records are written to `output/errors.json` together with the reason for the validation failure.

The absolute `product_url` is used as the unique identity of each book so duplicate books are not stored.

## Polite Scraping Rules

The scraper follows several rules to reduce unnecessary requests and behave responsibly:

* Sends an identifying User-Agent with every real request.
* Uses a timeout so requests do not wait forever.
* Waits at least 0.5 seconds between real requests.
* Checks the HTTP status code before parsing a response.
* Retries a timeout or `5xx` server error only once.
* Does not retry `403` or `404` responses.
* Caches downloaded HTML and uses the cached copy during development instead of repeatedly requesting the same page.

The `cache/` directory is excluded from Git because cached HTML files are local development data and do not need to be committed.

## Validation and Storage

Raw scraped values are cleaned before storage. For example:

```text
"£51.77" → 51.77
```

Both values are preserved:

```json
{
  "price_text": "£51.77",
  "price_gbp": 51.77
}
```

Valid records are stored in:

```text
output/books.json
```

Invalid records and their reasons are stored in:

```text
output/errors.json
```

Running the scraper multiple times still produces exactly 60 unique records rather than adding duplicates.

## Run Report

Every run creates `output/run-report.json` containing the start time, duration, number of pages fetched, cache hits, valid records, invalid records, and failed pages.

Example from the deliberate failure test:

```json
{
  "start_time": "2026-08-16T11:38:25Z",
  "duration_seconds": 3.19,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 1
}
```

The 63 cache hits represent the 3 catalogue pages and 60 individual book pages that were already stored locally.

## Why No Browser Automation?

This project does not need Playwright, Selenium, or another browser automation tool because the required book data is already present in the HTML returned by the server. Using a browser would add unnecessary time, memory use, and complexity.

## Ethics

When an official API exists, I would prefer using it instead of scraping the website directly. I would not bypass logins, paywalls, access restrictions, or other blocks. I would also collect only the data needed for the task and check a site's rules and terms before reusing this scraper elsewhere.

## Limitation

This scraper is designed specifically for the current HTML structure of Books to Scrape. If the website changes its page structure or CSS selectors, the extraction logic may need to be updated.
