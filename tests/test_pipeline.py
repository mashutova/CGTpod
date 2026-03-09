"""Tests for the pipeline orchestrator."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from cgtpod.config import Config
from cgtpod.models import Article
from cgtpod.pipeline import run_daily


def _make_cgt_articles(count: int) -> list[Article]:
    """Create N CGT-relevant test articles."""
    return [
        Article(
            id=f"art{i}",
            title=f"CGT Article {i}",
            url=f"https://example.com/{i}",
            summary=f"CGT summary {i}",
            source="test",
            published_date=datetime(2026, 3, 9, tzinfo=timezone.utc),
            is_cgt_relevant=True,
            cgt_confidence=0.9,
        )
        for i in range(count)
    ]


@patch("cgtpod.pipeline.publish_episode")
@patch("cgtpod.pipeline.generate_episode")
@patch("cgtpod.pipeline.classify_articles")
@patch("cgtpod.pipeline.fetch_all_feeds")
def test_daily_generates_episode_above_threshold(
    mock_fetch, mock_classify, mock_generate, mock_publish, tmp_path
):
    """Daily pipeline generates episode when >= 3 CGT articles."""
    articles = _make_cgt_articles(5)
    mock_fetch.return_value = articles
    mock_classify.return_value = articles

    mock_episode = MagicMock()
    mock_episode.articles = articles
    mock_episode.episode_id = "test-ep"
    mock_generate.return_value = mock_episode

    config = Config(
        anthropic_api_key="test",
        data_dir=str(tmp_path / "data"),
        min_articles_for_daily=3,
        github_repo="test/repo",
    )

    # Create data dir
    (tmp_path / "data").mkdir()

    result = run_daily(config)
    assert result is not None
    mock_generate.assert_called_once()
    mock_publish.assert_called_once()


@patch("cgtpod.pipeline.classify_articles")
@patch("cgtpod.pipeline.fetch_all_feeds")
def test_daily_accumulates_below_threshold(mock_fetch, mock_classify, tmp_path):
    """Daily pipeline accumulates when < 3 CGT articles."""
    articles = _make_cgt_articles(2)
    mock_fetch.return_value = articles
    mock_classify.return_value = articles

    config = Config(
        anthropic_api_key="test",
        data_dir=str(tmp_path / "data"),
        min_articles_for_daily=3,
    )

    (tmp_path / "data").mkdir()

    result = run_daily(config)
    assert result is None

    # Check articles were accumulated
    acc_path = tmp_path / "data" / "accumulated.json"
    assert acc_path.exists()


@patch("cgtpod.pipeline.fetch_all_feeds")
def test_daily_no_new_articles(mock_fetch, tmp_path):
    """Daily pipeline exits cleanly when no new articles."""
    mock_fetch.return_value = []

    config = Config(
        anthropic_api_key="test",
        data_dir=str(tmp_path / "data"),
    )

    (tmp_path / "data").mkdir()

    result = run_daily(config)
    assert result is None
