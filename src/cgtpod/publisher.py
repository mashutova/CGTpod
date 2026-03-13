"""Publish podcast episodes via self-hosted RSS on GitHub Pages + GitHub Releases."""

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

from cgtpod.config import Config
from cgtpod.models import Episode

logger = logging.getLogger(__name__)

# iTunes namespace for podcast RSS
ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"

# Podcast metadata
PODCAST_TITLE = "CGT News Podcast"
PODCAST_DESCRIPTION = (
    "Your daily automated digest of cell and gene therapy news, "
    "covering CAR-T, gene editing, CRISPR, viral vectors, and more."
)
PODCAST_AUTHOR = "CGTPod Bot"
PODCAST_LANGUAGE = "en"
PODCAST_CATEGORY = "Science"


def publish_episode(episode: Episode, config: Config, docs_dir: Path) -> str:
    """Publish an episode: upload MP3 to GitHub Releases, update RSS feed.

    Args:
        episode: Episode with audio_path set.
        config: Pipeline configuration.
        docs_dir: Path to docs/ directory (served by GitHub Pages).

    Returns:
        URL of the published episode audio.
    """
    if not episode.audio_path or not Path(episode.audio_path).exists():
        raise FileNotFoundError(f"Audio file not found: {episode.audio_path}")

    # Upload MP3 to GitHub Releases
    audio_url = _upload_to_release(episode, config)

    # Update RSS feed
    feed_path = docs_dir / "feed.xml"
    _update_rss_feed(episode, audio_url, feed_path, config)

    episode.published = True
    episode.published_url = audio_url
    logger.info("Published episode %s: %s", episode.episode_id, audio_url)
    return audio_url


def _upload_to_release(episode: Episode, config: Config) -> str:
    """Upload MP3 to a GitHub Release and return the asset download URL."""
    audio_path = Path(episode.audio_path)
    tag = f"episode-{episode.episode_id}"

    logger.info("Creating GitHub release %s...", tag)

    # Strip any residual HTML from title and description
    clean_title = re.sub(r"<[^>]+>", " ", episode.title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    clean_notes = re.sub(r"<[^>]+>", " ", episode.description[:500])
    clean_notes = re.sub(r"\s+", " ", clean_notes).strip()

    try:
        # Create release and upload asset using gh CLI
        result = subprocess.run(
            [
                "gh", "release", "create", tag,
                str(audio_path),
                "--title", clean_title,
                "--notes", clean_notes,
                "--repo", config.github_repo,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Release created: %s", result.stdout.strip())

        # Get the asset download URL
        asset_url = (
            f"https://github.com/{config.github_repo}/releases/download/"
            f"{tag}/{audio_path.name}"
        )
        return asset_url

    except subprocess.CalledProcessError as e:
        logger.error("Failed to create release: %s\n%s", e.stdout, e.stderr)
        raise


def _update_rss_feed(
    episode: Episode, audio_url: str, feed_path: Path, config: Config
) -> None:
    """Regenerate the podcast RSS feed XML with the new episode."""
    feed_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing episodes from feed log
    log_path = feed_path.parent / "feed_episodes.json"
    episodes_log = _load_episodes_log(log_path)

    # Add new episode
    audio_path = Path(episode.audio_path)
    file_size = audio_path.stat().st_size if audio_path.exists() else 0

    episodes_log.append({
        "episode_id": episode.episode_id,
        "title": episode.title,
        "description": episode.description,
        "audio_url": audio_url,
        "file_size": file_size,
        "duration_seconds": episode.duration_seconds,
        "pub_date": datetime.now(timezone.utc).isoformat(),
    })

    # Save updated log
    _save_episodes_log(episodes_log, log_path)

    # Generate RSS XML
    base_url = f"https://{config.github_repo.split('/')[0]}.github.io/{config.github_repo.split('/')[-1]}"
    xml_str = _generate_rss_xml(episodes_log, base_url)
    feed_path.write_text(xml_str, encoding="utf-8")
    logger.info("Updated RSS feed at %s (%d episodes)", feed_path, len(episodes_log))


def _generate_rss_xml(episodes: list[dict], base_url: str) -> str:
    """Generate podcast-compliant RSS XML."""
    rss = Element("rss", {
        "version": "2.0",
        "xmlns:itunes": ITUNES_NS,
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
    })

    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = PODCAST_TITLE
    SubElement(channel, "description").text = PODCAST_DESCRIPTION
    SubElement(channel, "language").text = PODCAST_LANGUAGE
    SubElement(channel, "link").text = base_url
    SubElement(channel, f"{{{ITUNES_NS}}}author").text = PODCAST_AUTHOR
    SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"

    category = SubElement(channel, f"{{{ITUNES_NS}}}category")
    category.set("text", PODCAST_CATEGORY)

    # Add episodes (newest first)
    for ep in reversed(episodes):
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "description").text = ep.get("description", "")
        SubElement(item, "guid", {"isPermaLink": "false"}).text = ep["episode_id"]

        pub_date = datetime.fromisoformat(ep["pub_date"])
        SubElement(item, "pubDate").text = format_datetime(pub_date)

        enclosure = SubElement(item, "enclosure")
        enclosure.set("url", ep["audio_url"])
        enclosure.set("length", str(ep.get("file_size", 0)))
        enclosure.set("type", "audio/mpeg")

        if ep.get("duration_seconds"):
            mins = ep["duration_seconds"] // 60
            secs = ep["duration_seconds"] % 60
            SubElement(item, f"{{{ITUNES_NS}}}duration").text = f"{mins}:{secs:02d}"

    # Pretty print
    raw_xml = tostring(rss, encoding="unicode", xml_declaration=True)
    return parseString(raw_xml).toprettyxml(indent="  ")


def _load_episodes_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_episodes_log(episodes: list[dict], path: Path) -> None:
    with open(path, "w") as f:
        json.dump(episodes, f, indent=2)
