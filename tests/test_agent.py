"""Tests for EmailAgent — the conversation orchestrator."""

import json
import pytest

from unittest.mock import MagicMock, patch

from src.agent.core import EmailAgent
from src.models.conversation import ConversationState


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

VALID_LLM_REPLY = json.dumps({
    "reply": "Wie heisst dein Kind?",
    "updates": {},
    "next_step": "child_name",
    "registration_complete": False,
    "language": "de",
})

COMPLETION_LLM_REPLY = json.dumps({
    "reply": "Vielen Dank, dein Kind ist angemeldet!",
    "updates": {},
    "next_step": "done",
    "registration_complete": True,
    "language": "de",
})


@pytest.fixture
def mock_kb():
    kb = MagicMock()
    kb.get_all.return_value = "# FAQ\nSome knowledge base content."
    return kb


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.load.return_value = None  # no prior conversation by default
    store.save_registration.return_value = ("anna.muster@example.com", 1)
    return store


@pytest.fixture
def mock_notifier():
    return MagicMock()


@pytest.fixture
def agent(mock_kb, mock_store, mock_notifier):
    return EmailAgent(
        model="anthropic/claude-opus-4-6",
        kb=mock_kb,
        store=mock_store,
        notifier=mock_notifier,
    )


# ---------------------------------------------------------------------------
# process_message — new conversation
# ---------------------------------------------------------------------------


class TestProcessMessageNewConversation:
    def test_creates_new_state_when_none_exists(self, agent, mock_store):
        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Hallo")

        saved_state = mock_store.save.call_args[0][0]
        assert saved_state.conversation_id == "anna.muster@example.com"

    def test_returns_llm_reply_text(self, agent):
        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            reply = agent.process_message("anna.muster@example.com", "Hallo")

        assert reply == "Wie heisst dein Kind?"

    def test_user_message_added_to_history(self, agent, mock_store):
        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Hallo, ich möchte anmelden")

        state = mock_store.save.call_args[0][0]
        assert any(m.role == "user" and "anmelden" in m.content for m in state.messages)

    def test_assistant_reply_added_to_history(self, agent, mock_store):
        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Hallo")

        state = mock_store.save.call_args[0][0]
        assert any(m.role == "assistant" for m in state.messages)

    def test_normalizes_email_key(self, agent, mock_store):
        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("Anna.Muster@EXAMPLE.COM", "Hallo")

        state = mock_store.save.call_args[0][0]
        assert state.conversation_id == "anna.muster@example.com"


# ---------------------------------------------------------------------------
# process_message — existing conversation
# ---------------------------------------------------------------------------


class TestProcessMessageExistingConversation:
    def test_loads_existing_state(self, agent, mock_store, fresh_state):
        mock_store.load.return_value = fresh_state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Lena")

        mock_store.load.assert_called_once()

    def test_flow_step_updated(self, agent, mock_store, fresh_state):
        mock_store.load.return_value = fresh_state

        reply_with_step = json.dumps({
            "reply": "Wann ist Lena geboren?",
            "updates": {"child.fullName": "Lena"},
            "next_step": "child_dob",
            "registration_complete": False,
            "language": "de",
        })

        with patch("src.llm.complete", return_value=reply_with_step):
            agent.process_message("anna.muster@example.com", "Lena")

        state = mock_store.save.call_args[0][0]
        assert state.flow_step == "child_dob"


# ---------------------------------------------------------------------------
# process_message — registration completion
# ---------------------------------------------------------------------------


class TestRegistrationCompletion:
    def test_notifier_called_on_completion(self, agent, mock_store, mock_notifier, complete_registration):
        state = ConversationState(
            conversation_id="anna.muster@example.com",
            parent_email="anna.muster@example.com",
        )
        state.registration = complete_registration
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=COMPLETION_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Ja, alles korrekt")

        mock_notifier.notify_admin.assert_called_once()

    def test_state_marked_completed(self, agent, mock_store, complete_registration):
        state = ConversationState(
            conversation_id="anna.muster@example.com",
            parent_email="anna.muster@example.com",
        )
        state.registration = complete_registration
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=COMPLETION_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Ja")

        saved = mock_store.save.call_args[0][0]
        assert saved.completed is True

    def test_notifier_not_called_when_already_completed(self, agent, mock_store, mock_notifier, complete_registration):
        state = ConversationState(
            conversation_id="anna.muster@example.com",
            parent_email="anna.muster@example.com",
        )
        state.registration = complete_registration
        state.completed = True  # already done
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=COMPLETION_LLM_REPLY):
            agent.process_message("anna.muster@example.com", "Noch eine Frage")

        mock_notifier.notify_admin.assert_not_called()


# ---------------------------------------------------------------------------
# Fallback on LLM error
# ---------------------------------------------------------------------------


class TestFallbackOnLLMError:
    def test_returns_german_fallback_by_default(self, agent):
        with patch("src.llm.complete", side_effect=RuntimeError("API down")):
            reply = agent.process_message("anna.muster@example.com", "Hallo")

        assert "technisches Problem" in reply or "Entschuldigung" in reply

    def test_returns_english_fallback_when_language_is_en(self, agent, mock_store, fresh_state):
        fresh_state.language = "en"
        mock_store.load.return_value = fresh_state

        with patch("src.llm.complete", side_effect=RuntimeError("API down")):
            reply = agent.process_message("anna.muster@example.com", "Hello")

        assert "technical issue" in reply.lower() or "sorry" in reply.lower()


# ---------------------------------------------------------------------------
# _parse_llm_response
# ---------------------------------------------------------------------------


class TestParseLlmResponse:
    def test_parses_plain_json(self, agent):
        payload = '{"reply": "Hi", "updates": {}, "next_step": "greeting", "registration_complete": false, "language": "de"}'
        result = agent._parse_llm_response(payload)
        assert result["reply"] == "Hi"

    def test_parses_fenced_json(self, agent):
        payload = '```json\n{"reply": "Hi", "updates": {}}\n```'
        result = agent._parse_llm_response(payload)
        assert result["reply"] == "Hi"

    def test_parses_json_embedded_in_text(self, agent):
        payload = 'Sure, here is the response: {"reply": "Hi", "updates": {}}'
        result = agent._parse_llm_response(payload)
        assert result["reply"] == "Hi"

    def test_falls_back_to_raw_text_when_no_json(self, agent):
        result = agent._parse_llm_response("Ich bin ein Hilfsroboter")
        assert result["reply"] == "Ich bin ein Hilfsroboter"

    def test_fallback_has_safe_defaults(self, agent):
        result = agent._parse_llm_response("plain text")
        assert result["registration_complete"] is False
        assert result["updates"] == {}


# ---------------------------------------------------------------------------
# _apply_updates
# ---------------------------------------------------------------------------


class TestApplyUpdates:
    def test_sets_child_name(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {"child.fullName": "Lena Muster"})
        assert fresh_state.registration.child.full_name == "Lena Muster"

    def test_sets_child_dob(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {"child.dateOfBirth": "2022-03-15"})
        assert fresh_state.registration.child.date_of_birth == "2022-03-15"

    def test_sets_parent_email(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {"parentGuardian.email": "test@example.com"})
        assert fresh_state.registration.parent_guardian.email == "test@example.com"

    def test_sets_emergency_contact(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {"emergencyContact.phone": "079 111 22 33"})
        assert fresh_state.registration.emergency_contact.phone == "079 111 22 33"

    def test_sets_booking_days(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {
            "booking.selectedDays": [{"day": "wednesday", "type": "indoor"}]
        })
        assert fresh_state.registration.booking.selected_days[0].day == "wednesday"

    def test_ignores_none_values(self, agent, fresh_state):
        fresh_state.registration.child.full_name = "Lena"
        agent._apply_updates(fresh_state, {"child.fullName": None})
        assert fresh_state.registration.child.full_name == "Lena"

    def test_ignores_unknown_keys(self, agent, fresh_state):
        agent._apply_updates(fresh_state, {"unknown.key": "value"})  # should not raise
