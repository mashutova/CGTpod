"""Tests for CGT article classification."""

import json
from unittest.mock import MagicMock, patch

from cgtpod.classifier import _parse_response, classify_articles, filter_cgt_relevant
from cgtpod.config import Config
from cgtpod.models import Article


def test_parse_response_plain_json():
    text = json.dumps([
        {"id": "abc", "relevant": True, "confidence": 0.9, "reason": "CAR-T"},
    ])
    result = _parse_response(text)
    assert len(result) == 1
    assert result[0]["relevant"] is True


def test_parse_response_markdown_code_block():
    text = '```json\n[{"id": "abc", "relevant": true, "confidence": 0.9, "reason": "CAR-T"}]\n```'
    result = _parse_response(text)
    assert len(result) == 1


def test_filter_cgt_relevant(sample_articles):
    relevant = filter_cgt_relevant(sample_articles)
    assert len(relevant) == 3
    assert all(a.is_cgt_relevant for a in relevant)


def test_classify_articles_no_api_key(sample_articles):
    """Without API key, articles are returned unmodified."""
    config = Config(anthropic_api_key="")
    result = classify_articles(sample_articles, config)
    assert len(result) == len(sample_articles)


def test_classify_articles_mock_api(sample_articles):
    """Test classification with mocked Claude API."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"id": a.id, "relevant": True, "confidence": 0.9, "reason": "CGT"}
        for a in sample_articles
    ]))]

    config = Config(anthropic_api_key="test-key")

    with patch("cgtpod.classifier.anthropic.Anthropic") as MockClient:
        mock_client = MockClient.return_value
        mock_client.messages.create.return_value = mock_response

        result = classify_articles(sample_articles, config)

    assert all(a.is_cgt_relevant for a in result)
    assert all(a.cgt_confidence == 0.9 for a in result)
