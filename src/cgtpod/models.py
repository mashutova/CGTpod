"""Data models for articles and episodes flowing through the pipeline."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """A single news article from an RSS feed."""

    id: str  # SHA-256[:16] of URL
    title: str
    url: str
    summary: str
    source: str  # "endpoints_news" | "fierce_biotech"
    published_date: datetime
    fetched_date: datetime = field(default_factory=datetime.utcnow)
    is_cgt_relevant: bool | None = None
    cgt_reason: str = ""
    cgt_confidence: float = 0.0

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "source": self.source,
            "published_date": self.published_date.isoformat(),
            "fetched_date": self.fetched_date.isoformat(),
            "is_cgt_relevant": self.is_cgt_relevant,
            "cgt_reason": self.cgt_reason,
            "cgt_confidence": self.cgt_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Article":
        """Deserialize from dict."""
        return cls(
            id=data["id"],
            title=data["title"],
            url=data["url"],
            summary=data["summary"],
            source=data["source"],
            published_date=datetime.fromisoformat(data["published_date"]),
            fetched_date=datetime.fromisoformat(data["fetched_date"]),
            is_cgt_relevant=data.get("is_cgt_relevant"),
            cgt_reason=data.get("cgt_reason", ""),
            cgt_confidence=data.get("cgt_confidence", 0.0),
        )


@dataclass
class Episode:
    """A podcast episode generated from CGT-relevant articles."""

    episode_id: str  # e.g., "2026-03-09-daily" or "2026-W11-weekly"
    title: str
    description: str
    articles: list[Article]
    episode_type: str = "daily"  # "daily" | "weekly"
    audio_path: str = ""
    duration_seconds: int = 0
    published: bool = False
    published_url: str = ""
    created_date: datetime = field(default_factory=datetime.utcnow)
