"""Centralized configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    """All pipeline configuration, loaded from environment variables."""

    # RSS feed URLs
    feed_urls: dict[str, list[str]] = field(default_factory=lambda: {
        "endpoints_news": [
            "https://endpoints.news/feed/",
        ],
        "fierce_biotech": [
            "https://www.fiercebiotech.com/rss/xml",
        ],
    })
    feed_timeout: int = 30

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"

    # Audio generation
    audio_backend: str = "podcastfy"  # "podcastfy" or "notebooklm"
    tts_backend: str = "edge"  # "edge" (free) or "openai"
    openai_api_key: str = ""

    # Pipeline
    min_articles_for_daily: int = 3
    data_dir: str = "data"

    # GitHub (for publishing)
    github_repo: str = ""  # e.g., "mashutova/CGTpod"
    github_token: str = ""

    # Logging
    log_level: str = "INFO"


def load_config() -> Config:
    """Load configuration from environment variables with defaults."""
    return Config(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        claude_model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"),
        audio_backend=os.environ.get("AUDIO_BACKEND", "podcastfy"),
        tts_backend=os.environ.get("TTS_BACKEND", "edge"),
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        min_articles_for_daily=int(os.environ.get("MIN_ARTICLES", "3")),
        data_dir=os.environ.get("DATA_DIR", "data"),
        github_repo=os.environ.get("GITHUB_REPOSITORY", ""),
        github_token=os.environ.get("GITHUB_TOKEN", ""),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
