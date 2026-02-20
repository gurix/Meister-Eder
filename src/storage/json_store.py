"""File-based JSON storage for conversations and completed registrations."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models.conversation import ConversationState
from ..models.registration import RegistrationData

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationStore:
    """Persists ConversationState objects as JSON files on disk.

    Directory layout::

        data/
          conversations/   # one file per email thread
          registrations/   # one file per completed registration
    """

    def __init__(self, data_dir: Path) -> None:
        self._conversations_dir = data_dir / "conversations"
        self._registrations_dir = data_dir / "registrations"
        self._conversations_dir.mkdir(parents=True, exist_ok=True)
        self._registrations_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Conversation CRUD
    # ------------------------------------------------------------------

    def load(self, conversation_id: str) -> ConversationState | None:
        """Load a conversation by ID. Returns None if not found."""
        path = self._conversation_path(conversation_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ConversationState.from_dict(data)
        except Exception:
            logger.exception("Failed to load conversation %s", conversation_id)
            return None

    def save(self, state: ConversationState) -> None:
        """Persist a conversation state to disk."""
        path = self._conversation_path(state.conversation_id)
        try:
            path.write_text(
                json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save conversation %s", state.conversation_id)

    def delete(self, conversation_id: str) -> None:
        """Remove a conversation file (e.g., after retention period expires)."""
        path = self._conversation_path(conversation_id)
        if path.exists():
            path.unlink()

    def list_incomplete(self) -> list[ConversationState]:
        """Return all conversations that are not yet completed."""
        states: list[ConversationState] = []
        for path in self._conversations_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                state = ConversationState.from_dict(data)
                if not state.completed:
                    states.append(state)
            except Exception:
                logger.warning("Could not read conversation file %s", path)
        return states

    # ------------------------------------------------------------------
    # Registration storage
    # ------------------------------------------------------------------

    def save_registration(self, state: ConversationState) -> str:
        """Write the completed registration to disk and return its ID."""
        registration_id = str(uuid.uuid4())
        record = state.registration.to_dict()
        record["metadata"] = {
            "registrationId": registration_id,
            "submittedAt": _now(),
            "channel": "email",
            "conversationId": state.conversation_id,
        }

        path = self._registrations_dir / f"{registration_id}.json"
        try:
            path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.info("Saved registration %s", registration_id)
        except Exception:
            logger.exception("Failed to save registration %s", registration_id)

        return registration_id

    def load_registration(self, registration_id: str) -> dict | None:
        """Load a completed registration record by ID."""
        path = self._registrations_dir / f"{registration_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load registration %s", registration_id)
            return None

    def list_registrations(self) -> list[dict]:
        """Return all completed registration records."""
        records: list[dict] = []
        for path in sorted(self._registrations_dir.glob("*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                logger.warning("Could not read registration file %s", path)
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conversation_path(self, conversation_id: str) -> Path:
        """Sanitise the conversation ID to produce a safe filename."""
        safe = (
            conversation_id
            .replace("/", "_")
            .replace("\\", "_")
            .replace("<", "")
            .replace(">", "")
            .replace("@", "_at_")
        )[:200]
        return self._conversations_dir / f"{safe}.json"
