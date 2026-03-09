"""Shared test fixtures."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cgtpod.config import Config
from cgtpod.models import Article

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_articles() -> list[Article]:
    """A mix of CGT-relevant and non-relevant articles."""
    return [
        Article(
            id="abc123",
            title="Novartis CAR-T therapy Kymriah shows durable responses",
            url="https://example.com/car-t",
            summary="CAR-T therapy data from Novartis",
            source="endpoints_news",
            published_date=datetime(2026, 3, 9, tzinfo=timezone.utc),
            is_cgt_relevant=True,
            cgt_confidence=0.95,
            cgt_reason="CAR-T cell therapy",
        ),
        Article(
            id="def456",
            title="CRISPR Therapeutics advances exa-cel manufacturing",
            url="https://example.com/crispr",
            summary="CRISPR gene editing therapy manufacturing",
            source="endpoints_news",
            published_date=datetime(2026, 3, 8, tzinfo=timezone.utc),
            is_cgt_relevant=True,
            cgt_confidence=0.92,
            cgt_reason="Gene editing, CRISPR",
        ),
        Article(
            id="ghi789",
            title="bluebird bio gene therapy lovo-cel gets CHMP positive opinion",
            url="https://example.com/bluebird",
            summary="Gene therapy regulatory approval",
            source="endpoints_news",
            published_date=datetime(2026, 3, 8, tzinfo=timezone.utc),
            is_cgt_relevant=True,
            cgt_confidence=0.98,
            cgt_reason="Gene therapy, regulatory",
        ),
        Article(
            id="jkl012",
            title="Eli Lilly acquires obesity drug maker",
            url="https://example.com/lilly",
            summary="GLP-1 obesity drug acquisition",
            source="endpoints_news",
            published_date=datetime(2026, 3, 9, tzinfo=timezone.utc),
            is_cgt_relevant=False,
            cgt_confidence=0.05,
            cgt_reason="Not CGT-related",
        ),
    ]


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Config pointing to temp directories."""
    return Config(
        anthropic_api_key="test-key",
        data_dir=str(tmp_path / "data"),
        github_repo="test/repo",
        github_token="test-token",
    )


@pytest.fixture
def endpoints_rss_xml() -> str:
    return (FIXTURES_DIR / "endpoints_rss.xml").read_text()


@pytest.fixture
def fierce_rss_xml() -> str:
    return (FIXTURES_DIR / "fierce_rss.xml").read_text()
