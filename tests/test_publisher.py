"""Tests for RSS feed generation and publishing."""

import xml.etree.ElementTree as ET
from pathlib import Path

from cgtpod.publisher import _generate_rss_xml


def test_generate_rss_xml_basic():
    episodes = [
        {
            "episode_id": "2026-03-09-daily",
            "title": "CGT Daily News - March 09, 2026",
            "description": "Today's CGT news highlights",
            "audio_url": "https://github.com/test/repo/releases/download/ep1/ep1.mp3",
            "file_size": 5000000,
            "duration_seconds": 300,
            "pub_date": "2026-03-09T10:00:00+00:00",
        }
    ]

    xml_str = _generate_rss_xml(episodes, "https://test.github.io/CGTpod")

    # Parse and validate
    root = ET.fromstring(xml_str)
    assert root.tag == "rss"

    channel = root.find("channel")
    assert channel is not None
    assert channel.find("title").text == "CGT News Podcast"

    items = channel.findall("item")
    assert len(items) == 1
    assert items[0].find("title").text == "CGT Daily News - March 09, 2026"

    enclosure = items[0].find("enclosure")
    assert enclosure is not None
    assert enclosure.get("type") == "audio/mpeg"
    assert "ep1.mp3" in enclosure.get("url")


def test_generate_rss_xml_multiple_episodes():
    episodes = [
        {
            "episode_id": f"2026-03-0{i}-daily",
            "title": f"Episode {i}",
            "description": f"Description {i}",
            "audio_url": f"https://example.com/ep{i}.mp3",
            "file_size": 5000000,
            "pub_date": f"2026-03-0{i}T10:00:00+00:00",
        }
        for i in range(1, 4)
    ]

    xml_str = _generate_rss_xml(episodes, "https://test.github.io/CGTpod")
    root = ET.fromstring(xml_str)
    items = root.find("channel").findall("item")
    assert len(items) == 3


def test_generate_rss_xml_empty():
    xml_str = _generate_rss_xml([], "https://test.github.io/CGTpod")
    root = ET.fromstring(xml_str)
    items = root.find("channel").findall("item")
    assert len(items) == 0
