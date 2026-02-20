"""File-based JSON storage for conversations and completed registrations.

Conversations are keyed by the sender's normalized email address so that a
parent who sends a new email (instead of replying) continues the same
conversation. Completed registrations are stored with versioning so every
update produces a new numbered version rather than overwriting the original.

Directory layout::

    data/
      conversations/
        parent_at_example.com.json   # one file per unique sender address
      registrations/
        parent_at_example.com/
          v1_2024-09-15T10-30-00Z.json   # initial registration
          v2_2024-10-03T14-22-10Z.json   # updated registration
          current.json                    # copy of the latest version
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from ..models.conversation import ConversationState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """Return a canonical email address for matching and storage.

    Lowercases and strips whitespace.  ``Maria@Example.com`` → ``maria@example.com``.
    """
    return email.strip().lower()


def _email_to_filename(email: str) -> str:
    """Convert a normalized email address to a safe filename stem.

    ``parent@example.com`` → ``parent_at_example.com``
    """
    return normalize_email(email).replace("@", "_at_")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp_for_filename() -> str:
    """Return a filesystem-safe ISO-8601-ish timestamp (no colons)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _diff_registrations(old: dict, new: dict) -> dict[str, tuple]:
    """Return a mapping of field_path → (old_value, new_value) for changed fields."""
    changes: dict[str, tuple] = {}

    def _flatten(d: dict, prefix: str = "") -> dict:
        out: dict = {}
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
        return out

    old_flat = _flatten(old)
    new_flat = _flatten(new)

    all_keys = set(old_flat) | set(new_flat)
    for key in sorted(all_keys):
        o = old_flat.get(key)
        n = new_flat.get(key)
        if o != n:
            changes[key] = (o, n)

    return changes


# ---------------------------------------------------------------------------
# ConversationStore
# ---------------------------------------------------------------------------

class ConversationStore:
    """Persists ConversationState and registration versions on disk."""

    def __init__(self, data_dir: Path) -> None:
        self._conversations_dir = data_dir / "conversations"
        self._registrations_dir = data_dir / "registrations"
        self._conversations_dir.mkdir(parents=True, exist_ok=True)
        self._registrations_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Conversation CRUD — keyed by normalized email address
    # ------------------------------------------------------------------

    def load(self, email_address: str) -> ConversationState | None:
        """Load a conversation by sender email address. Returns None if not found."""
        path = self._conversation_path(email_address)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ConversationState.from_dict(data)
        except Exception:
            logger.exception("Failed to load conversation for %s", email_address)
            return None

    # Alias for clarity in call sites that emphasise the email-lookup semantic
    find_by_email = load

    def save(self, state: ConversationState) -> None:
        """Persist a conversation state to disk."""
        path = self._conversation_path(state.parent_email or state.conversation_id)
        try:
            path.write_text(
                json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            logger.exception("Failed to save conversation for %s", state.conversation_id)

    def delete(self, email_address: str) -> None:
        """Remove a conversation file."""
        path = self._conversation_path(email_address)
        if path.exists():
            path.unlink()

    def list_incomplete(self) -> list[ConversationState]:
        """Return all conversations that have not yet been completed."""
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
    # Versioned registration storage
    # ------------------------------------------------------------------

    def save_registration(self, state: ConversationState) -> tuple[str, int]:
        """Store the first version of a completed registration.

        Returns:
            Tuple of (registration_dir_key, version_number).
        """
        email_key = _email_to_filename(state.parent_email or state.conversation_id)
        reg_dir = self._registrations_dir / email_key
        reg_dir.mkdir(parents=True, exist_ok=True)

        version = 1
        record = self._build_record(state.registration.to_dict(), version, state)

        self._write_version(reg_dir, version, record)
        logger.info("Saved initial registration v%d for %s", version, email_key)
        return email_key, version

    def save_registration_version(
        self,
        state: ConversationState,
        change_summary: dict[str, tuple],
    ) -> tuple[str, int]:
        """Store an updated registration as a new version.

        Args:
            state: Current conversation state with updated registration data.
            change_summary: Dict of field_path → (old_value, new_value).

        Returns:
            Tuple of (registration_dir_key, new_version_number).
        """
        email_key = _email_to_filename(state.parent_email or state.conversation_id)
        reg_dir = self._registrations_dir / email_key
        reg_dir.mkdir(parents=True, exist_ok=True)

        history = self.get_registration_history(state.parent_email or state.conversation_id)
        version = len(history) + 1

        record = self._build_record(state.registration.to_dict(), version, state)
        record["metadata"]["changeSummary"] = {
            k: {"old": v[0], "new": v[1]} for k, v in change_summary.items()
        }

        self._write_version(reg_dir, version, record)
        logger.info("Saved registration v%d for %s", version, email_key)
        return email_key, version

    def get_registration_history(self, email_address: str) -> list[dict]:
        """Return all registration versions for an email address, oldest first."""
        email_key = _email_to_filename(email_address)
        reg_dir = self._registrations_dir / email_key
        if not reg_dir.exists():
            return []

        records: list[dict] = []
        for path in sorted(reg_dir.glob("v*.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                logger.warning("Could not read registration version %s", path)
        return records

    def get_current_registration(self, email_address: str) -> dict | None:
        """Return the latest registration version for an email address."""
        email_key = _email_to_filename(email_address)
        current_path = self._registrations_dir / email_key / "current.json"
        if not current_path.exists():
            return None
        try:
            return json.loads(current_path.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("Failed to load current registration for %s", email_address)
            return None

    def list_registrations(self) -> list[dict]:
        """Return the current (latest) registration for every known email address."""
        records: list[dict] = []
        for email_dir in sorted(self._registrations_dir.iterdir()):
            if not email_dir.is_dir():
                continue
            current = email_dir / "current.json"
            if current.exists():
                try:
                    records.append(json.loads(current.read_text(encoding="utf-8")))
                except Exception:
                    logger.warning("Could not read %s", current)
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conversation_path(self, email_address: str) -> Path:
        return self._conversations_dir / f"{_email_to_filename(email_address)}.json"

    @staticmethod
    def _build_record(reg_data: dict, version: int, state: ConversationState) -> dict:
        record = dict(reg_data)
        record["metadata"] = {
            "version": version,
            "submittedAt": _now(),
            "channel": "email",
            "parentEmail": state.parent_email,
            "conversationId": state.conversation_id,
        }
        return record

    @staticmethod
    def _write_version(reg_dir: Path, version: int, record: dict) -> None:
        ts = _timestamp_for_filename()
        version_path = reg_dir / f"v{version}_{ts}.json"
        version_path.write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # Keep current.json as a plain copy of the latest version
        (reg_dir / "current.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
        )
