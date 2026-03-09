"""Top-level pipeline orchestrator for daily and weekly podcast generation."""

import argparse
import logging
import sys
from pathlib import Path

from cgtpod.audio import generate_episode
from cgtpod.classifier import classify_articles, filter_cgt_relevant
from cgtpod.config import Config, load_config
from cgtpod.feeds import fetch_all_feeds
from cgtpod.models import Episode
from cgtpod.publisher import publish_episode
from cgtpod.state import ArticleAccumulator, ArticleTracker

logger = logging.getLogger(__name__)


def run_daily(config: Config) -> Episode | None:
    """Execute the daily pipeline.

    1. Fetch all RSS feeds.
    2. Filter out previously used articles.
    3. Classify remaining articles for CGT relevance.
    4. If >= min_articles: generate daily episode.
       Else: accumulate articles for weekly digest.
    """
    data_dir = Path(config.data_dir)
    tracker = ArticleTracker(data_dir / "article_log.json")
    accumulator = ArticleAccumulator(data_dir / "accumulated.json")

    # Fetch and filter
    all_articles = fetch_all_feeds(config)
    new_articles = tracker.filter_new(all_articles)

    if not new_articles:
        logger.info("No new articles found. Nothing to do.")
        return None

    # Classify for CGT relevance
    classified = classify_articles(new_articles, config)
    cgt_articles = filter_cgt_relevant(classified)

    logger.info("CGT-relevant articles today: %d", len(cgt_articles))

    if len(cgt_articles) >= config.min_articles_for_daily:
        # Generate daily episode
        episode = generate_episode(cgt_articles, "daily", config)
        _publish_and_track(episode, tracker, accumulator, config)
        return episode
    else:
        # Accumulate for weekly digest
        if cgt_articles:
            accumulator.add(cgt_articles)
        logger.info(
            "Below threshold (%d < %d). Accumulated %d articles total.",
            len(cgt_articles), config.min_articles_for_daily, accumulator.count(),
        )
        return None


def run_weekly(config: Config) -> Episode | None:
    """Execute the weekly digest pipeline.

    Combines newly fetched CGT articles with all accumulated articles.
    Generates episode regardless of article count (even 1 article).
    """
    data_dir = Path(config.data_dir)
    tracker = ArticleTracker(data_dir / "article_log.json")
    accumulator = ArticleAccumulator(data_dir / "accumulated.json")

    # Fetch new articles
    all_articles = fetch_all_feeds(config)
    new_articles = tracker.filter_new(all_articles)

    # Classify new articles
    cgt_new = []
    if new_articles:
        classified = classify_articles(new_articles, config)
        cgt_new = filter_cgt_relevant(classified)

    # Combine with accumulated
    accumulated = accumulator.get_all()
    all_cgt = accumulated + cgt_new

    # Deduplicate by ID
    seen: set[str] = set()
    unique_cgt = []
    for a in all_cgt:
        if a.id not in seen:
            seen.add(a.id)
            unique_cgt.append(a)

    if not unique_cgt:
        logger.info("No CGT articles for weekly digest. Skipping.")
        return None

    logger.info(
        "Weekly digest: %d articles (%d accumulated + %d new)",
        len(unique_cgt), len(accumulated), len(cgt_new),
    )

    episode = generate_episode(unique_cgt, "weekly", config)
    _publish_and_track(episode, tracker, accumulator, config)
    return episode


def _publish_and_track(
    episode: Episode,
    tracker: ArticleTracker,
    accumulator: ArticleAccumulator,
    config: Config,
) -> None:
    """Publish episode and update state."""
    docs_dir = Path("docs")

    try:
        publish_episode(episode, config, docs_dir)
    except Exception as e:
        logger.error("Failed to publish episode %s: %s", episode.episode_id, e)
        # Still mark articles as used so we don't retry them
        # but don't clear accumulator so weekly can pick them up

    tracker.mark_used(episode.articles, episode.episode_id)
    accumulator.clear()

    # Periodic cleanup
    tracker.cleanup_old(days=90)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="CGT News Podcast Pipeline")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly"],
        default="daily",
        help="Pipeline mode: daily (default) or weekly digest",
    )
    args = parser.parse_args()

    config = load_config()

    # Set up logging
    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting CGTPod pipeline (mode: %s)", args.mode)

    try:
        if args.mode == "weekly":
            episode = run_weekly(config)
        else:
            episode = run_daily(config)

        if episode:
            logger.info("Episode generated: %s", episode.title)
        else:
            logger.info("No episode generated this run.")

    except Exception:
        logger.exception("Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
