"""Tests for audio generation module."""

import pytest

from cgtpod.audio import _build_episode, _prepare_content_text


def test_build_daily_episode(sample_articles):
    episode = _build_episode(sample_articles, "daily")
    assert "daily" in episode.episode_id
    assert "Daily" in episode.title
    assert len(episode.articles) == 4


def test_build_weekly_episode(sample_articles):
    episode = _build_episode(sample_articles, "weekly")
    assert "weekly" in episode.episode_id
    assert "Weekly" in episode.title


def test_prepare_content_text(sample_articles):
    episode = _build_episode(sample_articles, "daily")
    content = _prepare_content_text(episode)

    assert "Story 1:" in content
    assert "CAR-T" in content
    assert "cell and gene therapy" in content
    assert "endpoints_news" in content


def test_notebooklm_not_implemented(sample_articles, test_config):
    """NotebookLM backend should raise NotImplementedError."""
    from cgtpod.audio import generate_episode
    from cgtpod.config import Config

    config = Config(audio_backend="notebooklm")

    with pytest.raises(NotImplementedError):
        generate_episode(sample_articles, "daily", config)
