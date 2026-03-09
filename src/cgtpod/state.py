"""Track used articles and accumulate articles between pipeline runs."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cgtpod.models import Article

logger = logging.getLogger(__name__)


class ArticleTracker:
    """Persistent tracker for used article IDs, stored as JSON.

    Format: {"article_id": {"episode_id": "...", "used_date": "..."}, ...}
    """

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._log: dict[str, dict] = self._load()

    def is_used(self, article: Article) -> bool:
        return article.id in self._log

    def mark_used(self, articles: list[Article], episode_id: str) -> None:
        for article in articles:
            self._log[article.id] = {
                "episode_id": episode_id,
                "used_date": datetime.now(timezone.utc).isoformat(),
                "title": article.title,
            }
        self._save()
        logger.info("Marked %d articles as used for episode %s", len(articles), episode_id)

    def filter_new(self, articles: list[Article]) -> list[Article]:
        new = [a for a in articles if not self.is_used(a)]
        logger.info("Filtered articles: %d total -> %d new", len(articles), len(new))
        return new

    def cleanup_old(self, days: int = 90) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)
        to_remove = []
        for aid, info in self._log.items():
            try:
                used = datetime.fromisoformat(info["used_date"]).timestamp()
                if used < cutoff:
                    to_remove.append(aid)
            except (KeyError, ValueError):
                continue

        for aid in to_remove:
            del self._log[aid]

        if to_remove:
            self._save()
            logger.info("Cleaned up %d old entries from article log", len(to_remove))

        return len(to_remove)

    def _load(self) -> dict:
        if not self.log_path.exists():
            return {}
        try:
            with open(self.log_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load article log, starting fresh: %s", e)
            return {}

    def _save(self) -> None:
        """Atomic write: write to temp file, then rename."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=self.log_path.parent, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._log, f, indent=2)
            os.replace(tmp_path, self.log_path)
        except Exception:
            os.unlink(tmp_path)
            raise


class ArticleAccumulator:
    """Store articles between pipeline runs for bundling into episodes.

    Articles are serialized as JSON dicts.
    """

    def __init__(self, path: Path):
        self.path = path
        self._articles: list[dict] = self._load()

    def add(self, articles: list[Article]) -> None:
        for a in articles:
            self._articles.append(a.to_dict())
        self._save()
        logger.info("Accumulated %d articles (total: %d)", len(articles), len(self._articles))

    def get_all(self) -> list[Article]:
        return [Article.from_dict(d) for d in self._articles]

    def count(self) -> int:
        return len(self._articles)

    def clear(self) -> None:
        self._articles = []
        self._save()
        logger.info("Cleared accumulated articles")

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            with open(self.path) as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not load accumulator, starting fresh: %s", e)
            return []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._articles, f, indent=2)
            os.replace(tmp_path, self.path)
        except Exception:
            os.unlink(tmp_path)
            raise
