"""Fetch and parse RSS feeds from Endpoints News and Fierce Biotech."""

import hashlib
import logging
import re
from datetime import datetime, timezone
from html import unescape

import feedparser
from dateutil.parser import parse as parse_date

from cgtpod.config import Config
from cgtpod.models import Article

logger = logging.getLogger(__name__)


class FeedFetchError(Exception):
    """Raised when an RSS feed cannot be fetched or parsed."""


def fetch_all_feeds(config: Config) -> list[Article]:
    """Fetch articles from all configured RSS feed URLs.

    Returns deduplicated list of Article objects, sorted by published_date desc.
    One failing feed does not block others.
    """
    all_articles: list[Article] = []

    for source_name, urls in config.feed_urls.items():
        for url in urls:
            try:
                articles = fetch_single_feed(url, source_name, config.feed_timeout)
                all_articles.extend(articles)
                logger.info("Fetched %d articles from %s (%s)", len(articles), source_name, url)
            except FeedFetchError:
                logger.warning("Failed to fetch feed: %s (%s)", source_name, url)

    # Deduplicate by article ID (URL hash)
    seen: set[str] = set()
    unique: list[Article] = []
    for article in all_articles:
        if article.id not in seen:
            seen.add(article.id)
            unique.append(article)

    # Sort by published date, newest first
    unique.sort(key=lambda a: a.published_date, reverse=True)

    logger.info("Total unique articles fetched: %d", len(unique))
    return unique


def fetch_single_feed(url: str, source_name: str, timeout: int = 30) -> list[Article]:
    """Fetch and parse a single RSS feed URL into Article objects."""
    feed = feedparser.parse(url, request_headers={"User-Agent": "CGTPod/1.0"})

    if feed.bozo and not feed.entries:
        raise FeedFetchError(f"Failed to parse feed {url}: {feed.bozo_exception}")

    if not feed.entries:
        logger.warning("Feed returned 0 entries: %s", url)
        return []

    articles = []
    for entry in feed.entries:
        try:
            article = _parse_entry(entry, source_name)
            articles.append(article)
        except (KeyError, ValueError) as e:
            logger.debug("Skipping malformed entry in %s: %s", url, e)

    return articles


def _parse_entry(entry: feedparser.FeedParserDict, source_name: str) -> Article:
    """Convert a single feedparser entry to an Article."""
    url = entry.get("link", "")
    if not url:
        raise ValueError("Entry has no link")

    title = unescape(entry.get("title", "Untitled"))

    # Extract summary text, stripping HTML
    raw_summary = entry.get("summary", "") or entry.get("description", "")
    summary = _strip_html(unescape(raw_summary))

    # Parse published date
    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if published:
        pub_date = datetime(*published[:6], tzinfo=timezone.utc)
    else:
        # Try parsing from string
        pub_str = entry.get("published", "") or entry.get("updated", "")
        if pub_str:
            pub_date = parse_date(pub_str)
            if pub_date.tzinfo is None:
                pub_date = pub_date.replace(tzinfo=timezone.utc)
        else:
            pub_date = datetime.now(timezone.utc)

    return Article(
        id=_generate_article_id(url),
        title=title,
        url=url,
        summary=summary[:2000],  # Cap summary length
        source=source_name,
        published_date=pub_date,
    )


def _generate_article_id(url: str) -> str:
    """Generate a deterministic unique ID from article URL using SHA-256[:16]."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
