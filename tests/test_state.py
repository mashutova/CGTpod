"""Tests for article tracking and accumulation."""

from pathlib import Path

from cgtpod.state import ArticleAccumulator, ArticleTracker


def test_tracker_mark_and_check(tmp_path, sample_articles):
    tracker = ArticleTracker(tmp_path / "log.json")

    assert not tracker.is_used(sample_articles[0])

    tracker.mark_used(sample_articles[:2], "test-ep-1")

    assert tracker.is_used(sample_articles[0])
    assert tracker.is_used(sample_articles[1])
    assert not tracker.is_used(sample_articles[2])


def test_tracker_filter_new(tmp_path, sample_articles):
    tracker = ArticleTracker(tmp_path / "log.json")
    tracker.mark_used(sample_articles[:1], "test-ep-1")

    new = tracker.filter_new(sample_articles)
    assert len(new) == 3  # 4 total - 1 used = 3 new


def test_tracker_persistence(tmp_path, sample_articles):
    """Tracker state persists across instances."""
    log_path = tmp_path / "log.json"

    tracker1 = ArticleTracker(log_path)
    tracker1.mark_used(sample_articles[:1], "test-ep-1")

    tracker2 = ArticleTracker(log_path)
    assert tracker2.is_used(sample_articles[0])


def test_tracker_corrupted_file(tmp_path):
    """Tracker recovers from corrupted JSON."""
    log_path = tmp_path / "log.json"
    log_path.write_text("not valid json{{{")

    tracker = ArticleTracker(log_path)
    assert tracker._log == {}


def test_accumulator_add_get_clear(tmp_path, sample_articles):
    acc = ArticleAccumulator(tmp_path / "acc.json")

    assert acc.count() == 0

    acc.add(sample_articles[:2])
    assert acc.count() == 2

    retrieved = acc.get_all()
    assert len(retrieved) == 2
    assert retrieved[0].title == sample_articles[0].title

    acc.clear()
    assert acc.count() == 0


def test_accumulator_persistence(tmp_path, sample_articles):
    acc_path = tmp_path / "acc.json"

    acc1 = ArticleAccumulator(acc_path)
    acc1.add(sample_articles[:1])

    acc2 = ArticleAccumulator(acc_path)
    assert acc2.count() == 1
    assert acc2.get_all()[0].title == sample_articles[0].title


def test_accumulator_corrupted_file(tmp_path):
    acc_path = tmp_path / "acc.json"
    acc_path.write_text("broken json")

    acc = ArticleAccumulator(acc_path)
    assert acc.count() == 0
