"""Tests for RSS feed fetching and parsing."""

from unittest.mock import patch

import feedparser

from cgtpod.feeds import (
    _generate_article_id,
    _parse_entry,
    _strip_html,
    fetch_single_feed,
)


def test_strip_html():
    assert _strip_html("<p>Hello <b>world</b></p>") == "Hello world"
    assert _strip_html("No tags here") == "No tags here"
    assert _strip_html("  extra   spaces  ") == "extra spaces"


def test_generate_article_id():
    id1 = _generate_article_id("https://example.com/article1")
    id2 = _generate_article_id("https://example.com/article2")
    assert len(id1) == 16
    assert id1 != id2
    # Deterministic
    assert _generate_article_id("https://example.com/article1") == id1


def test_parse_entry_basic():
    entry = feedparser.FeedParserDict({
        "title": "Test Article",
        "link": "https://example.com/test",
        "summary": "<p>Article summary</p>",
        "published_parsed": (2026, 3, 9, 10, 0, 0, 0, 68, 0),
    })
    article = _parse_entry(entry, "test_source")
    assert article.title == "Test Article"
    assert article.url == "https://example.com/test"
    assert article.summary == "Article summary"
    assert article.source == "test_source"
    assert article.published_date.year == 2026


def test_parse_entry_html_entities():
    entry = feedparser.FeedParserDict({
        "title": "Drug &amp; Therapy Update",
        "link": "https://example.com/test",
        "summary": "CAR-T &amp; gene therapy",
        "published_parsed": (2026, 3, 9, 10, 0, 0, 0, 68, 0),
    })
    article = _parse_entry(entry, "test_source")
    assert article.title == "Drug & Therapy Update"
    assert article.summary == "CAR-T & gene therapy"


def test_parse_entry_html_tags_in_title():
    """HTML tags in titles (e.g. Fierce Biotech) are stripped."""
    entry = feedparser.FeedParserDict({
        "title": '<a href="https://www.fiercebiotech.com/biotech/ultragenyx">Ultragenyx gene therapy</a>',
        "link": "https://example.com/test",
        "summary": "A summary",
        "published_parsed": (2026, 3, 9, 10, 0, 0, 0, 68, 0),
    })
    article = _parse_entry(entry, "test_source")
    assert article.title == "Ultragenyx gene therapy"
    assert "<" not in article.title


def test_fetch_single_feed_from_fixture(endpoints_rss_xml):
    """Test parsing against saved RSS fixture."""
    parsed = feedparser.parse(endpoints_rss_xml)
    with patch("feedparser.parse", return_value=parsed):
        articles = fetch_single_feed(
            "https://endpoints.news/feed/", "endpoints_news"
        )

    assert len(articles) == 4
    assert articles[0].source == "endpoints_news"
    # Check CGT-relevant article is parsed
    titles = [a.title for a in articles]
    assert any("CAR-T" in t for t in titles)
    assert any("CRISPR" in t for t in titles)


def test_fetch_single_feed_fierce_fixture(fierce_rss_xml):
    """Test parsing Fierce Biotech RSS fixture."""
    parsed = feedparser.parse(fierce_rss_xml)
    with patch("feedparser.parse", return_value=parsed):
        articles = fetch_single_feed(
            "https://www.fiercebiotech.com/rss/xml", "fierce_biotech"
        )

    assert len(articles) == 3
    assert all(a.source == "fierce_biotech" for a in articles)
