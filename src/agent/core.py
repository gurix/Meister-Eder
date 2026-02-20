"""EmailAgent — the channel-agnostic conversation orchestrator."""

import json
import logging
import re
from datetime import datetime, timezone

from ..models.conversation import ConversationState, ChatMessage
from ..models.registration import BookingDay
from ..providers.base import LLMProvider, LLMMessage
from ..knowledge_base.loader import KnowledgeBase
from ..storage.json_store import ConversationStore
from ..notifications.notifier import AdminNotifier
from .prompts import build_system_prompt

logger = logging.getLogger(__name__)


class EmailAgent:
    """Processes one inbound message and returns the agent's reply text.

    All business logic (conversation flow, field extraction, validation,
    storage, notifications) lives here. Channel-specific I/O is handled
    by the caller.
    """

    def __init__(
        self,
        provider: LLMProvider,
        kb: KnowledgeBase,
        store: ConversationStore,
        notifier: AdminNotifier,
    ) -> None:
        self._provider = provider
        self._kb = kb
        self._store = store
        self._notifier = notifier

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_message(
        self,
        conversation_id: str,
        parent_email: str,
        message_text: str,
    ) -> str:
        """Process an inbound message and return the reply to send back.

        Args:
            conversation_id: Unique thread identifier (from email headers).
            parent_email: Sender's email address.
            message_text: Stripped plain-text body of the inbound email.

        Returns:
            Reply text to send to the parent.
        """
        # Load or create conversation state
        state = self._store.load(conversation_id)
        if state is None:
            state = ConversationState(
                conversation_id=conversation_id,
                parent_email=parent_email,
            )

        now = datetime.now(timezone.utc).isoformat()
        state.last_activity = now

        # Append the user's message to history
        state.messages.append(ChatMessage(role="user", content=message_text))

        # Build system prompt and conversation history for the LLM
        system = build_system_prompt(self._kb, state)
        llm_messages = [
            LLMMessage(role=m.role, content=m.content) for m in state.messages
        ]

        # Call the LLM
        try:
            response = self._provider.complete(system=system, messages=llm_messages)
            parsed = self._parse_llm_response(response.content)
        except Exception:
            logger.exception("LLM call failed for conversation %s", conversation_id)
            parsed = self._fallback_response(state)

        reply_text: str = parsed.get("reply", "")
        updates: dict = parsed.get("updates", {}) or {}
        next_step: str = parsed.get("next_step", state.flow_step)
        is_complete: bool = bool(parsed.get("registration_complete", False))
        language: str = parsed.get("language", state.language)

        # Apply extracted field updates
        self._apply_updates(state, updates)

        # Update conversation metadata
        state.flow_step = next_step
        state.language = language
        state.updated_at = now

        # Record the assistant reply
        state.messages.append(ChatMessage(role="assistant", content=reply_text))

        # Handle registration completion
        if is_complete and not state.completed:
            state.completed = True
            registration_id = self._store.save_registration(state)
            try:
                self._notifier.notify_admin(
                    registration=state.registration,
                    registration_id=registration_id,
                    conversation_id=state.conversation_id,
                    channel="email",
                )
            except Exception:
                logger.exception("Failed to send admin notification for %s", registration_id)
            logger.info("Registration complete: %s", registration_id)

        # Persist conversation state
        self._store.save(state)

        return reply_text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_llm_response(self, content: str) -> dict:
        """Extract the JSON payload from the LLM's output."""
        text = content.strip()

        # Strip markdown code fences if present
        fence_pattern = re.compile(r"^```(?:json)?\s*\n(.*?)\n```\s*$", re.DOTALL)
        match = fence_pattern.match(text)
        if match:
            text = match.group(1).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: find the first {...} block
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass

        logger.warning("Could not parse LLM response as JSON; using raw text as reply.")
        return {
            "reply": content,
            "updates": {},
            "next_step": "greeting",
            "registration_complete": False,
            "language": "de",
        }

    def _fallback_response(self, state: ConversationState) -> dict:
        """Return a safe fallback when the LLM call fails."""
        if state.language == "en":
            msg = (
                "I'm sorry, I'm having a technical issue right now. "
                "Please try again in a moment or contact us directly."
            )
        else:
            msg = (
                "Entschuldigung, ich habe gerade ein technisches Problem. "
                "Bitte versuche es gleich nochmal oder kontaktiere uns direkt."
            )
        return {
            "reply": msg,
            "updates": {},
            "next_step": state.flow_step,
            "registration_complete": False,
            "language": state.language,
        }

    def _apply_updates(self, state: ConversationState, updates: dict) -> None:
        """Write extracted field values into the RegistrationData object."""
        reg = state.registration

        field_map = {
            "child.fullName":               lambda v: setattr(reg.child, "full_name", v),
            "child.dateOfBirth":            lambda v: setattr(reg.child, "date_of_birth", v),
            "child.specialNeeds":           lambda v: setattr(reg.child, "special_needs", v),
            "parentGuardian.fullName":      lambda v: (
                setattr(reg.parent_guardian, "full_name", v),
                setattr(state, "parent_name", v),
            ),
            "parentGuardian.streetAddress": lambda v: setattr(reg.parent_guardian, "street_address", v),
            "parentGuardian.postalCode":    lambda v: setattr(reg.parent_guardian, "postal_code", str(v)),
            "parentGuardian.city":          lambda v: setattr(reg.parent_guardian, "city", v),
            "parentGuardian.phone":         lambda v: setattr(reg.parent_guardian, "phone", v),
            "parentGuardian.email":         lambda v: setattr(reg.parent_guardian, "email", v),
            "emergencyContact.fullName":    lambda v: setattr(reg.emergency_contact, "full_name", v),
            "emergencyContact.phone":       lambda v: setattr(reg.emergency_contact, "phone", v),
        }

        for key, value in updates.items():
            if value is None:
                continue

            if key in field_map:
                field_map[key](value)
            elif key == "booking.playgroupTypes" and isinstance(value, list):
                reg.booking.playgroup_types = value
            elif key == "booking.selectedDays" and isinstance(value, list):
                reg.booking.selected_days = [
                    BookingDay(day=d["day"], type=d["type"])
                    for d in value
                    if isinstance(d, dict) and "day" in d and "type" in d
                ]
            else:
                logger.debug("Unknown update key ignored: %s", key)
