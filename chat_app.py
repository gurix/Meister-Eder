#!/usr/bin/env python3
"""Meister-Eder — Web Chat Interface for Spielgruppe Pumuckl.

Usage
-----
Copy `.env.example` to `.env`, fill in your credentials, then run:

    chainlit run chat_app.py

The app serves a web chat interface at http://localhost:8000.
Parents can register their child or ask questions in real time.

Environment variables (see .env.example):
  AI_MODEL             litellm model string  (default: anthropic/claude-opus-4-6)
  ANTHROPIC_API_KEY    Required for Anthropic models
  SMTP_HOST / SMTP_PORT  For admin notifications (optional in dev)
  ADMIN_EMAIL_INDOOR / ADMIN_EMAIL_OUTDOOR / ADMIN_EMAIL_CC  Notification routing
  DATA_DIR             Directory for completed registration JSON  (default: data/)
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import chainlit as cl

from src import llm
from src.agent.prompts import build_system_prompt
from src.agent.response_parser import apply_updates, fallback_message, parse_llm_response
from src.config import Config
from src.knowledge_base.loader import KnowledgeBase
from src.models.conversation import ChatMessage, ConversationState
from src.models.registration import RegistrationData
from src.notifications.i18n import get_strings
from src.notifications.notifier import AdminNotifier
from src.storage.json_store import ConversationStore, _diff_registrations
from src.utils.tokens import EMAIL_PATTERN, generate_resume_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared components — initialised once when the server starts.
# These are read-only after startup and safe to share across sessions.
# ---------------------------------------------------------------------------
_config = Config.from_env()
_kb = KnowledgeBase(_config.knowledge_base_dir)
_store = ConversationStore(_config.data_dir)
_notifier = AdminNotifier(
    smtp_host=_config.smtp_host,
    smtp_port=_config.smtp_port,
    username=_config.imap_username,
    password=_config.imap_password,
    use_tls=_config.smtp_use_tls,
    from_email=_config.registration_email,
    indoor_email=_config.admin_email_indoor,
    outdoor_email=_config.admin_email_outdoor,
    cc_emails=[e.strip() for e in _config.admin_email_cc.split(",") if e.strip()],
    model=_config.simple_model,
)

# ---------------------------------------------------------------------------
# Welcome message (German default, per spec)
# ---------------------------------------------------------------------------
_WELCOME_DE = (
    "Hallo! Ich bin der Anmeldeassistent der Spielgruppe Pumuckl. "
    "Ich kann dir helfen, dein Kind anzumelden, oder deine Fragen zur Spielgruppe beantworten.\n\n"
    "Du kannst mir auf die Sprache schreiben die du am besten kannst — ich antworte in derselben Sprache.\n\n"
    "Damit du deine Anmeldung später fortsetzen kannst, falls das Gespräch unterbrochen wird: "
    "Wie lautet deine E-Mail-Adresse?"
)

_EMAIL_RE = re.compile(EMAIL_PATTERN)

def _handle_email_lookup(state: ConversationState, message_content: str) -> Optional[str]:
    """Extract email from message, look up existing state, and mutate *state* in place.

    Returns the reply text to send immediately (and the caller should ``return``),
    or ``None`` if processing should continue normally.

    Responsibilities:
    - Detect an email address in *message_content*
    - Query the store for an existing registration under that email
    - Merge stored registration data into *state* for cross-channel resume
    - Build and return the appropriate reply for the parent, or None to continue
    """
    email_match = _EMAIL_RE.search(message_content)
    if not email_match:
        return None

    email = email_match.group().lower()
    state.parent_email = email
    state.channel = "chat"
    existing_state = _store.find_by_email(email)

    if existing_state and not existing_state.completed:
        # Resume existing incomplete registration (possibly from email channel)
        current_session_id = state.conversation_id
        current_messages = state.messages
        current_token = state.resume_token
        # Restore registration data from stored state
        state.registration = existing_state.registration
        state.flow_step = existing_state.flow_step
        state.language = existing_state.language
        state.parent_name = existing_state.parent_name
        state.conversation_id = current_session_id
        state.messages = current_messages
        state.resume_token = current_token or existing_state.resume_token
        # Keep channel as "chat" since we're continuing in the chat channel
        state.channel = "chat"
        return _build_resume_summary(existing_state)

    if existing_state and existing_state.completed:
        # Registration already completed — show status with channel info
        state.completed = existing_state.completed
        state.registration = existing_state.registration
        state.flow_step = "complete"
        return _build_completed_summary(existing_state)

    # New registration — continue normally
    state.flow_step = "greeting"
    return None


def _handle_registration_complete(state: ConversationState) -> None:
    """Persist a newly completed registration and notify admin and parent.

    Assumes ``state.completed`` has already been set to ``True`` by the caller.
    Handles all exceptions internally so that notification failures never abort
    the conversation.
    """
    try:
        email_key, version = _store.save_registration(state)
        _notifier.notify_admin(
            registration=state.registration,
            registration_id=email_key,
            version=version,
            conversation_id=state.conversation_id,
            channel="chat",
        )
        logger.info("Registration complete for session %s", state.conversation_id)
    except Exception:
        logger.exception(
            "Failed to save/notify for session %s", state.conversation_id
        )
    try:
        _notifier.notify_parent(
            registration=state.registration,
            language=state.language,
            resume_token=state.resume_token,
        )
    except Exception:
        logger.exception(
            "Failed to send parent confirmation for session %s", state.conversation_id
        )


def _build_resume_summary(existing: ConversationState) -> str:
    """Build a human-readable resume message in the parent's language.

    Uses the same LLM-based i18n system as the confirmation email so any
    language is supported automatically without hardcoded translations.
    """
    s = get_strings(existing.language, _config.simple_model)
    step_labels = s.get("chat_resume_steps", {})
    step_label = step_labels.get(existing.flow_step, existing.flow_step)
    channel_label = s.get(f"chat_resume_channel_{existing.channel}", existing.channel)
    child_name = existing.registration.child.full_name

    lines = [
        s.get("chat_resume_found", "Ich habe eine angefangene Anmeldung unter dieser E-Mail-Adresse gefunden!"),
        s.get("chat_resume_last_step", "Du hast zuletzt über den {channel} mit uns gesprochen und warst beim Schritt: {step}.").format(channel=channel_label, step=step_label),
    ]
    if child_name:
        lines.append(s.get("chat_resume_child", "Die Anmeldung ist für: {name}.").format(name=child_name))
    lines.append(s.get("chat_resume_continue", "Wir können dort weitermachen, wo du aufgehört hast. Lass uns fortfahren."))
    return "\n\n".join(lines)


def _build_completed_summary(existing: ConversationState) -> str:
    """Build a human-readable message for a found completed registration."""
    s = get_strings(existing.language, _config.simple_model)
    channel_label = s.get(f"chat_resume_channel_{existing.channel}", existing.channel)
    child_name = existing.registration.child.full_name
    playgroup_types = existing.registration.booking.playgroup_types

    lines = [
        s.get("chat_resume_completed", "Unter dieser E-Mail-Adresse ist bereits eine abgeschlossene Anmeldung gespeichert."),
    ]
    if child_name:
        lines.append(s.get("chat_resume_child_label", "Kind: {name}.").format(name=child_name))
    if playgroup_types:
        type_map = s.get("types", {"indoor": "Innenspielgruppe", "outdoor": "Waldspielgruppe"})
        types_str = " und ".join(type_map.get(t, t) for t in playgroup_types)
        lines.append(
            s.get("chat_resume_playgroup_label", "Spielgruppe: {types}.").format(types=types_str)
        )
    lines.append(s.get("chat_resume_submitted_via", "Diese Anmeldung wurde über den {channel} eingereicht. Falls du etwas ändern oder ein weiteres Kind anmelden möchtest, sag mir einfach Bescheid!").format(channel=channel_label))
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# Chainlit lifecycle handlers
# ---------------------------------------------------------------------------

@cl.on_chat_start
async def on_chat_start() -> None:
    """Initialise a fresh conversation state and greet the parent.

    If cl.user_session already holds state (WebSocket reconnect after a
    network drop), replay the existing message history so the parent sees
    the full conversation rather than a blank screen.
    """
    existing = cl.user_session.get("state")
    if existing:
        # Reconnected — restore visual history from our stored state
        state = ConversationState.from_dict(existing)
        logger.info(
            "Session reconnected: %s (%d messages)",
            state.conversation_id,
            len(state.messages),
        )
        for msg in state.messages:
            author = "Spielgruppe Pumuckl" if msg.role == "assistant" else "Du"
            await cl.Message(content=msg.content, author=author).send()
        return

    # Brand new session
    session_id = str(uuid.uuid4())
    state = ConversationState(conversation_id=session_id)
    state.flow_step = "email_first"
    state.channel = "chat"
    state.resume_token = generate_resume_token()
    # Store the welcome in history so it's replayed if the session reconnects.
    state.messages.append(ChatMessage(role="assistant", content=_WELCOME_DE))
    cl.user_session.set("state", state.to_dict())
    logger.info("Chat session started: %s", session_id)
    await cl.Message(content=_WELCOME_DE).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Process one parent message and stream the agent's reply."""
    # --- Restore state from session ---
    state = ConversationState.from_dict(cl.user_session.get("state"))
    now = datetime.now(timezone.utc).isoformat()
    state.last_activity = now

    # Append parent's message to history and persist immediately so that any
    # WebSocket reconnect during the LLM call can replay the full conversation.
    state.messages.append(ChatMessage(role="user", content=message.content))
    cl.user_session.set("state", state.to_dict())

    # --- Handle email_first step: extract email and check for existing conversation ---
    if state.flow_step == "email_first" and state.parent_email == "":
        reply = _handle_email_lookup(state, message.content)
        if reply is not None:
            state.messages.append(ChatMessage(role="assistant", content=reply))
            _store.save(state)
            cl.user_session.set("state", state.to_dict())
            await cl.Message(content=reply).send()
            return
        if state.parent_email:
            # New registration path — state already mutated by _handle_email_lookup
            _store.save(state)
            cl.user_session.set("state", state.to_dict())

    # --- Build system prompt ---
    system = build_system_prompt(_kb, state)

    # --- Call LLM natively async (supports extended thinking; no event-loop blocking) ---
    try:
        full_content = await llm.acomplete(
            _config.ai_model, system, state.messages, _config.thinking_budget
        )
    except Exception:
        logger.exception("LLM call failed for session %s", state.conversation_id)
        error_text = fallback_message(state.language)
        await cl.Message(content=error_text).send()
        return

    # --- Parse and apply LLM response ---
    parsed = parse_llm_response(full_content)

    reply_text: str = parsed.get("reply", full_content)
    updates: dict = parsed.get("updates", {}) or {}
    next_step: str = parsed.get("next_step", state.flow_step)
    is_complete: bool = bool(parsed.get("registration_complete", False))
    language: str = parsed.get("language", state.language)
    intent: str = parsed.get("intent", "")

    apply_updates(state, updates)
    state.flow_step = next_step
    state.language = language
    state.updated_at = now

    # Send the reply text to the parent (only the human-readable reply, not the JSON wrapper)
    await cl.Message(content=reply_text).send()

    # Append assistant reply to history
    state.messages.append(ChatMessage(role="assistant", content=reply_text))

    # --- Handle registration completion ---
    if is_complete and not state.completed:
        state.completed = True
        _handle_registration_complete(state)

    # --- Handle post-completion update intent ---
    if state.completed and intent == "update" and any(v is not None for v in updates.values()):
        _handle_registration_update(state)

    # --- Handle status_query intent ---
    if intent == "status_query" and state.completed:
        logger.info("Status query for session %s", state.conversation_id)
        # TODO: send a structured status summary back to the parent — e.g. show
        # the registered child's name, selected playgroup days, and next steps
        # (fee payment, trial day confirmation).  For now the LLM reply_text
        # already covers basic status questions; a dedicated handler would allow
        # a guaranteed consistent response independent of LLM output.

    # --- Handle resend_confirmation intent ---
    if intent == "resend_confirmation" and state.completed:
        try:
            _notifier.notify_parent(
                registration=state.registration,
                language=state.language,
                resume_token=state.resume_token,
            )
            logger.info("Resent parent confirmation for session %s", state.conversation_id)
        except Exception:
            logger.exception(
                "Failed to resend parent confirmation for session %s", state.conversation_id
            )

    # --- Handle new-child reset ---
    if state.completed and intent == "new_child":
        state.registration = RegistrationData()
        state.completed = False
        state.flow_step = "child_name"
        logger.info("New child registration started for session %s", state.conversation_id)

    # --- Persist updated state ---
    cl.user_session.set("state", state.to_dict())
    if state.parent_email:
        _store.save(state)


@cl.on_chat_end
async def on_chat_end() -> None:
    """Log session end. Hook for future email-reminder integration."""
    state_dict = cl.user_session.get("state")
    if state_dict:
        conversation_id = state_dict.get("conversation_id", "unknown")
        completed = state_dict.get("completed", False)
        logger.info(
            "Chat session ended: %s (completed=%s)", conversation_id, completed
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _handle_registration_update(state: ConversationState) -> None:
    """Version the registration record and notify admin of changes."""
    # Re-apply and diff from the stored current version
    current = _store.get_current_registration(state.conversation_id)
    if current is None:
        return

    change_summary = _diff_registrations(current, state.registration.to_dict())
    if not change_summary:
        return

    try:
        email_key, version = _store.save_registration_version(state, change_summary)
        _notifier.notify_registration_update(
            registration=state.registration,
            registration_id=email_key,
            version=version,
            change_summary=change_summary,
            conversation_id=state.conversation_id,
        )
        logger.info(
            "Registration updated to v%d for session %s", version, state.conversation_id
        )
    except Exception:
        logger.exception(
            "Failed to save update for session %s", state.conversation_id
        )
