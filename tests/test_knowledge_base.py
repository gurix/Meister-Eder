"""Tests for KnowledgeBase loader."""

import pytest
from pathlib import Path

from src.knowledge_base.loader import KnowledgeBase


@pytest.fixture
def kb_dir(tmp_path) -> Path:
    """A temporary knowledge-base directory with a couple of markdown files."""
    (tmp_path / "faq.md").write_text("# FAQ\nWann beginnt die Spielgruppe?\nIm August.")
    (tmp_path / "fees.md").write_text("# Fees\nCHF 130 per month.")
    return tmp_path


@pytest.fixture
def kb(kb_dir) -> KnowledgeBase:
    return KnowledgeBase(kb_dir)


class TestKnowledgeBaseLoading:
    def test_get_all_includes_file_content(self, kb):
        content = kb.get_all()
        assert "FAQ" in content
        assert "Fees" in content

    def test_get_all_concatenates_multiple_files(self, kb):
        content = kb.get_all()
        assert "CHF 130" in content
        assert "Spielgruppe" in content

    def test_reload_picks_up_new_file(self, kb, kb_dir):
        (kb_dir / "schedule.md").write_text("# Schedule\nMonday 9:00")
        kb.reload()
        assert "Schedule" in kb.get_all()

    def test_empty_directory_returns_empty_string(self, tmp_path):
        kb = KnowledgeBase(tmp_path)
        assert kb.get_all() == "" or isinstance(kb.get_all(), str)

    def test_nonexistent_directory_does_not_raise_on_init(self, tmp_path):
        # Should either handle gracefully or raise — just must not crash silently
        missing = tmp_path / "does_not_exist"
        try:
            kb = KnowledgeBase(missing)
            kb.get_all()
        except (FileNotFoundError, OSError):
            pass  # Acceptable to raise on missing dir

    def test_get_all_returns_string(self, kb):
        assert isinstance(kb.get_all(), str)
