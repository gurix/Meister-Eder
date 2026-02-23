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
import uuid
from datetime import datetime, timezone

import chainlit as cl

from src import llm
from src.agent.prompts import build_system_prompt
from src.agent.response_parser import apply_updates, fallback_message, parse_llm_response
from src.config import Config
from src.knowledge_base.loader import KnowledgeBase
from src.models.conversation import ChatMessage, ConversationState
from src.models.registration import RegistrationData
from src.notifications.notifier import AdminNotifier
from src.storage.json_store import ConversationStore, _diff_registrations

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
    "Du kannst mir auf Deutsch oder Englisch schreiben — ich antworte in derselben Sprache.\n\n"
    "Womit kann ich dir helfen?"
)


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
            )
        except Exception:
            logger.exception(
                "Failed to send parent confirmation for session %s", state.conversation_id
            )

    # --- Handle post-completion update intent ---
    if state.completed and intent == "update" and any(v is not None for v in updates.values()):
        _handle_registration_update(state)

    # --- Handle new-child reset ---
    if state.completed and intent == "new_child":
        state.registration = RegistrationData()
        state.completed = False
        state.flow_step = "child_name"
        logger.info("New child registration started for session %s", state.conversation_id)

    # --- Persist updated state ---
    cl.user_session.set("state", state.to_dict())


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
