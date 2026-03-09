"""Generate podcast audio from CGT-relevant articles.

Primary backend: Podcastfy + Edge TTS (free).
Future: NotebookLM Podcast API (when access is granted).
"""

import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cgtpod.config import Config
from cgtpod.models import Article, Episode

logger = logging.getLogger(__name__)


def generate_episode(
    articles: list[Article],
    episode_type: str,
    config: Config,
    output_dir: Path | None = None,
) -> Episode:
    """Generate a podcast episode from CGT-relevant articles.

    Args:
        articles: CGT-relevant articles to discuss.
        episode_type: "daily" or "weekly".
        config: Pipeline configuration.
        output_dir: Directory to save MP3. Defaults to temp dir.

    Returns:
        Episode object with audio_path populated.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="cgtpod_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build episode metadata
    episode = _build_episode(articles, episode_type)

    # Generate audio based on configured backend
    if config.audio_backend == "notebooklm":
        audio_path = _generate_notebooklm(episode, output_dir, config)
    else:
        audio_path = _generate_podcastfy(episode, output_dir, config)

    episode.audio_path = str(audio_path)
    logger.info("Generated episode: %s (%s)", episode.episode_id, audio_path)
    return episode


def _build_episode(articles: list[Article], episode_type: str) -> Episode:
    """Construct episode metadata from articles."""
    now = datetime.now(timezone.utc)

    if episode_type == "weekly":
        week_num = now.isocalendar()[1]
        episode_id = f"{now.year}-W{week_num:02d}-weekly"
        title = f"CGT Weekly Digest - Week {week_num}, {now.year}"
    else:
        episode_id = f"{now.strftime('%Y-%m-%d')}-daily"
        title = f"CGT Daily News - {now.strftime('%B %d, %Y')}"

    # Build description from article titles
    article_list = "\n".join(f"- {a.title}" for a in articles[:10])
    description = f"Today's CGT news highlights:\n{article_list}"

    return Episode(
        episode_id=episode_id,
        title=title,
        description=description,
        articles=articles,
        episode_type=episode_type,
    )


def _prepare_content_text(episode: Episode) -> str:
    """Format articles into structured text for podcast generation."""
    sections = []
    for i, article in enumerate(episode.articles, 1):
        sections.append(
            f"## Story {i}: {article.title}\n"
            f"Source: {article.source}\n"
            f"{article.summary}\n"
        )

    return (
        f"# {episode.title}\n\n"
        "The following are today's most important stories in cell and gene therapy. "
        "Discuss each story in detail, explaining why it matters for the CGT field, "
        "what the implications are for patients, researchers, and the industry.\n\n"
        + "\n".join(sections)
    )


def _generate_podcastfy(episode: Episode, output_dir: Path, config: Config) -> Path:
    """Generate podcast audio using Podcastfy + Edge TTS."""
    try:
        from podcastfy.client import generate_podcast
    except ImportError:
        logger.error("podcastfy not installed. Run: pip install podcastfy")
        raise

    content = _prepare_content_text(episode)
    output_file = output_dir / f"{episode.episode_id}.mp3"

    # Write content to a temp file for podcastfy
    content_file = output_dir / f"{episode.episode_id}_content.txt"
    content_file.write_text(content)

    tts_model = "edge" if config.tts_backend == "edge" else "openai"

    logger.info("Generating podcast with Podcastfy (TTS: %s)...", tts_model)

    try:
        result = generate_podcast(
            urls=[str(content_file)],
            tts_model=tts_model,
            conversation_config={
                "podcast_name": "CGT News Podcast",
                "podcast_tagline": "Your daily dose of cell and gene therapy news",
                "creativity": 0.7,
                "roles_person1": "Host",
                "roles_person2": "Expert analyst",
                "dialogue_style": "informative and conversational",
                "engagement_techniques": "Ask follow-up questions, provide context",
                "output_language": "English",
            },
        )

        # Podcastfy returns the path to the generated audio
        if result and Path(result).exists():
            # Move to our output location
            Path(result).rename(output_file)
        else:
            raise RuntimeError(f"Podcastfy did not produce output: {result}")

    finally:
        # Clean up content file
        content_file.unlink(missing_ok=True)

    return output_file


def _generate_notebooklm(episode: Episode, output_dir: Path, config: Config) -> Path:
    """Generate podcast audio using NotebookLM Podcast API.

    Placeholder - requires Google Cloud project with Discovery Engine API access.
    """
    raise NotImplementedError(
        "NotebookLM Podcast API integration pending. "
        "Apply for access at https://cloud.google.com/gemini/enterprise/notebooklm-enterprise. "
        "Use AUDIO_BACKEND=podcastfy in the meantime."
    )
