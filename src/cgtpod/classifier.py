"""Classify articles for CGT relevance using Claude API."""

import json
import logging

import anthropic

from cgtpod.config import Config
from cgtpod.models import Article

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert in cell and gene therapy (CGT). Classify news articles as \
relevant or not relevant to CGT.

CGT-RELEVANT topics include:
- CAR-T cell therapy, TCR-T, TIL therapy, NK cell therapy
- Gene therapy (viral vectors: AAV, lentivirus, adenovirus)
- Gene editing (CRISPR/Cas9, base editing, prime editing)
- RNA therapeutics (mRNA, siRNA, ASO) for genetic diseases
- Oncolytic virotherapy
- Cell manufacturing, GMP processing, supply chain for CGT products
- Clinical trials for CGT products
- Regulatory approvals/decisions for CGT (FDA, EMA, MHRA)
- Companies developing CGT products
- Tissue engineering using genetic modification
- UK CGT deals, partnerships, funding

NOT CGT-relevant:
- General oncology without a CGT component
- Traditional small molecule drugs or antibodies (unless CGT-related)
- General biotech business news without CGT angle
- Diagnostics (unless directly supporting CGT delivery)

Respond with a JSON array. For each article, output:
{"id": "<article_id>", "relevant": true/false, "confidence": 0.0-1.0, "reason": "<brief reason>"}
"""


def classify_articles(articles: list[Article], config: Config) -> list[Article]:
    """Classify a batch of articles for CGT relevance using Claude.

    Sends all articles in a single API call for efficiency.
    Returns articles with classification fields populated.
    """
    if not articles:
        return []

    if not config.anthropic_api_key:
        logger.warning("No ANTHROPIC_API_KEY set, skipping classification")
        return articles

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    # Build user prompt with article data
    article_data = []
    for a in articles:
        article_data.append({
            "id": a.id,
            "title": a.title,
            "summary": a.summary[:500],  # First 500 chars to save tokens
            "source": a.source,
        })

    user_prompt = (
        "Classify the following articles for CGT relevance. "
        "Respond with ONLY a JSON array, no other text.\n\n"
        f"{json.dumps(article_data, indent=2)}"
    )

    try:
        response = client.messages.create(
            model=config.claude_model,
            max_tokens=1024,
            temperature=0.0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        response_text = response.content[0].text.strip()
        classifications = _parse_response(response_text)

        # Map classifications back to articles
        class_map = {c["id"]: c for c in classifications}
        for article in articles:
            if article.id in class_map:
                c = class_map[article.id]
                article.is_cgt_relevant = c.get("relevant", False)
                article.cgt_confidence = c.get("confidence", 0.0)
                article.cgt_reason = c.get("reason", "")

        relevant_count = sum(1 for a in articles if a.is_cgt_relevant)
        logger.info(
            "Classified %d articles: %d CGT-relevant, %d not relevant",
            len(articles), relevant_count, len(articles) - relevant_count,
        )

    except anthropic.APIError as e:
        logger.error("Claude API error during classification: %s", e)
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("Failed to parse classification response: %s", e)

    return articles


def _parse_response(text: str) -> list[dict]:
    """Parse Claude's JSON response, handling markdown code blocks."""
    # Strip markdown code block if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])

    return json.loads(text)


def filter_cgt_relevant(articles: list[Article]) -> list[Article]:
    """Return only articles classified as CGT-relevant."""
    return [a for a in articles if a.is_cgt_relevant]
