"""Load admin-editable knowledge-base markdown files into memory."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """Reads markdown files from *kb_dir* and exposes them as a single string."""

    def __init__(self, kb_dir: Path) -> None:
        self._dir = kb_dir
        self._content: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._dir.exists():
            logger.warning("Knowledge-base directory not found: %s", self._dir)
            return
        for path in sorted(self._dir.glob("*.md")):
            self._content[path.stem] = path.read_text(encoding="utf-8")
        logger.info("Loaded %d knowledge-base file(s) from %s", len(self._content), self._dir)

    def get_all(self) -> str:
        """Return every KB file concatenated with section headers."""
        if not self._content:
            return "(No knowledge-base content available.)"
        sections = [
            f"### {name.upper().replace('-', ' ')}\n\n{content}"
            for name, content in self._content.items()
        ]
        return "\n\n---\n\n".join(sections)

    def reload(self) -> None:
        """Re-read all files from disk (useful when admins update content)."""
        self._content = {}
        self._load()
