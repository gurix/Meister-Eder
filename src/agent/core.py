"""EmailAgent — the channel-agnostic conversation orchestrator."""

import logging
from datetime import datetime, timezone

from ..models.conversation import ConversationState, ChatMessage
from ..models.registration import RegistrationData
from .. import llm
from ..knowledge_base.loader import KnowledgeBase
from ..storage.json_store import ConversationStore, normalize_email, _diff_registrations
from ..notifications.notifier import AdminNotifier
from .prompts import build_system_prompt
from .response_parser import apply_updates, fallback_message, parse_llm_response

logger = logging.getLogger(__name__)


class EmailAgent:
    """Processes one inbound email and returns the agent's reply text.

    Conversations are identified by the sender's normalized email address, so
    a parent who composes a fresh email (instead of replying) continues their
    existing conversation seamlessly.

    All business logic lives here; channel I/O is handled by the caller.
    """

    def __init__(
        self,
        model: str,
        kb: KnowledgeBase,
        store: ConversationStore,
        notifier: AdminNotifier,
        thinking_budget: int | None = None,
    ) -> None:
        self._model = model
        self._thinking_budget = thinking_budget
        self._kb = kb
        self._store = store
        self._notifier = notifier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_message(
        self,
        parent_email: str,
        message_text: str,
        inbound_message_id: str = "",
    ) -> str:
        """Process one inbound message and return the reply text.

        Args:
            parent_email: Sender email address — used as conversation key.
            message_text: Stripped plain-text body of the inbound email.
            inbound_message_id: Message-ID of the inbound email (stored for
                reply threading headers; not used for conversation matching).

        Returns:
            Reply text to send back to the parent.
        """
        email_key = normalize_email(parent_email)

        # Load or create conversation state — keyed by email address
        state = self._store.load(email_key)
        if state is None:
            state = ConversationState(
                conversation_id=email_key,
                parent_email=email_key,
            )

        now = datetime.now(timezone.utc).isoformat()
        state.last_activity = now
        if inbound_message_id:
            state.last_inbound_message_id = inbound_message_id

        # Append the user's message to history
        state.messages.append(ChatMessage(role="user", content=message_text))

        # Route to the appropriate handler
        if state.completed:
            reply_text = self._handle_post_completion(state)
        else:
            reply_text = self._handle_registration(state)

        # Record the assistant reply and persist
        state.messages.append(ChatMessage(role="assistant", content=reply_text))
        state.updated_at = now
        self._store.save(state)

        return reply_text

    # ------------------------------------------------------------------
    # Registration flow
    # ------------------------------------------------------------------

    def _handle_registration(self, state: ConversationState) -> str:
        """Drive the in-progress registration conversation."""
        system = build_system_prompt(self._kb, state)

        try:
            content = llm.complete(self._model, system, state.messages, self._thinking_budget)
            parsed = self._parse_llm_response(content)
        except Exception:
            logger.exception("LLM call failed for %s", state.conversation_id)
            return self._fallback_message(state)

        reply_text: str = parsed.get("reply", "")
        updates: dict = parsed.get("updates", {}) or {}
        next_step: str = parsed.get("next_step", state.flow_step)
        is_complete: bool = bool(parsed.get("registration_complete", False))
        language: str = parsed.get("language", state.language)

        self._apply_updates(state, updates)
        state.flow_step = next_step
        state.language = language

        if is_complete and not state.completed:
            state.completed = True
            email_key, version = self._store.save_registration(state)
            try:
                self._notifier.notify_admin(
                    registration=state.registration,
                    registration_id=email_key,
                    version=version,
                    conversation_id=state.conversation_id,
                    channel="email",
                )
            except Exception:
                logger.exception("Failed to send admin notification for %s", email_key)
            try:
                self._notifier.notify_parent(
                    registration=state.registration,
                    language=state.language,
                )
            except Exception:
                logger.exception("Failed to send parent confirmation for %s", email_key)
            logger.info("Registration complete for %s", state.conversation_id)

        return reply_text

    # ------------------------------------------------------------------
    # Post-completion flow
    # ------------------------------------------------------------------

    def _handle_post_completion(self, state: ConversationState) -> str:
        """Handle messages received after a registration is already complete."""
        system = build_system_prompt(self._kb, state)

        try:
            content = llm.complete(self._model, system, state.messages, self._thinking_budget)
            parsed = self._parse_llm_response(content)
        except Exception:
            logger.exception("LLM call failed (post-completion) for %s", state.conversation_id)
            return self._fallback_message(state)

        reply_text: str = parsed.get("reply", "")
        intent: str = parsed.get("intent", "question")
        updates: dict = parsed.get("updates", {}) or {}
        language: str = parsed.get("language", state.language)
        state.language = language

        if intent == "update" and any(v is not None for v in updates.values()):
            self._handle_registration_update(state, updates)
        elif intent == "new_child":
            # Reset registration so a fresh flow begins in the next message
            state.registration = RegistrationData()
            state.completed = False
            state.flow_step = "child_name"
            logger.info("Starting new child registration for %s", state.conversation_id)

        return reply_text

    def _handle_registration_update(self, state: ConversationState, updates: dict) -> None:
        """Apply field updates, version the record, and notify the admin."""
        old_data = state.registration.to_dict()
        self._apply_updates(state, updates)
        new_data = state.registration.to_dict()

        change_summary = _diff_registrations(old_data, new_data)
        if not change_summary:
            return  # Nothing actually changed

        email_key, version = self._store.save_registration_version(state, change_summary)
        try:
            self._notifier.notify_registration_update(
                registration=state.registration,
                registration_id=email_key,
                version=version,
                change_summary=change_summary,
                conversation_id=state.conversation_id,
            )
        except Exception:
            logger.exception("Failed to send update notification for %s", email_key)
        logger.info("Registration updated to v%d for %s", version, state.conversation_id)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _parse_llm_response(self, content: str) -> dict:
        return parse_llm_response(content)

    def _fallback_message(self, state: ConversationState) -> str:
        return fallback_message(state.language)

    def _apply_updates(self, state: ConversationState, updates: dict) -> None:
        apply_updates(state, updates)
