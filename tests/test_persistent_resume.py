"""Tests for the Persistent Resume feature (PR #13).

Covers: resume_token field, cross-channel find_by_email, email extraction,
resume token format, and list_incomplete filtering.
"""

import re
import secrets
import string

import pytest

from chat_app import EMAIL_PATTERN
from src.models.conversation import ConversationState
from src.storage.json_store import ConversationStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path) -> ConversationStore:
    return ConversationStore(tmp_path)


# ---------------------------------------------------------------------------
# 1. ConversationState has resume_token field
# ---------------------------------------------------------------------------


class TestResumeTokenField:
    def test_default_resume_token_is_empty_string(self):
        state = ConversationState(conversation_id="test")
        assert hasattr(state, "resume_token")
        assert state.resume_token == ""

    def test_resume_token_survives_round_trip(self):
        state = ConversationState(conversation_id="test")
        state.resume_token = "ABC123"
        restored = ConversationState.from_dict(state.to_dict())
        assert restored.resume_token == "ABC123"

    def test_to_dict_includes_resume_token(self):
        state = ConversationState(conversation_id="test")
        state.resume_token = "XY9Z42"
        d = state.to_dict()
        assert "resume_token" in d
        assert d["resume_token"] == "XY9Z42"

    def test_from_dict_defaults_to_empty_when_key_missing(self):
        """Older persisted conversations without the key deserialise safely."""
        data = {
            "conversation_id": "old@example.com",
            "parent_email": "old@example.com",
            "language": "de",
            "flow_step": "greeting",
            "registration": {},
            "messages": [],
            "completed": False,
            "reminder_count": 0,
            "last_inbound_message_id": "",
            "loop_escalated": False,
            # resume_token intentionally absent
        }
        state = ConversationState.from_dict(data)
        assert state.resume_token == ""


# ---------------------------------------------------------------------------
# 2. Store find_by_email for cross-channel resume
# ---------------------------------------------------------------------------


class TestFindByEmail:
    def test_find_by_email_returns_state_from_any_channel(self, store):
        state = ConversationState(
            conversation_id="anna.muster@example.com",
            parent_email="anna.muster@example.com",
        )
        state.flow_step = "parent_contact"
        store.save(state)

        found = store.find_by_email("anna.muster@example.com")
        assert found is not None
        assert found.flow_step == "parent_contact"

    def test_find_by_email_returns_none_for_unknown(self, store):
        assert store.find_by_email("unknown@example.com") is None

    def test_find_by_email_case_insensitive(self, store):
        state = ConversationState(
            conversation_id="anna@example.com",
            parent_email="anna@example.com",
        )
        store.save(state)
        assert store.find_by_email("ANNA@EXAMPLE.COM") is not None

    def test_find_by_email_returns_correct_conversation_id(self, store):
        state = ConversationState(
            conversation_id="uuid-123",
        )
        state.parent_email = "anna@example.com"
        store.save(state)

        found = store.find_by_email("anna@example.com")
        assert found is not None
        assert found.conversation_id == "uuid-123"


# ---------------------------------------------------------------------------
# 3. Resume logic: incomplete conversation
# ---------------------------------------------------------------------------


class TestResumeLogic:
    def test_resume_offered_when_email_matches_incomplete(self, store):
        existing = ConversationState(
            conversation_id="existing-id",
            parent_email="anna@example.com",
        )
        existing.flow_step = "special_needs"
        existing.completed = False
        store.save(existing)

        found = store.find_by_email("anna@example.com")
        assert found is not None
        assert not found.completed
        assert found.flow_step == "special_needs"


# ---------------------------------------------------------------------------
# 4. Status shown when email matches completed
# ---------------------------------------------------------------------------


class TestCompletedConversation:
    def test_completed_conversation_found_by_email(
        self, store, fresh_state, complete_registration
    ):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        store.save(fresh_state)

        found = store.find_by_email(fresh_state.parent_email)
        assert found is not None
        assert found.completed


# ---------------------------------------------------------------------------
# 5. Email extraction from user message
# ---------------------------------------------------------------------------


class TestEmailExtraction:
    EMAIL_RE = re.compile(EMAIL_PATTERN)

    def test_extracts_email_from_german_message(self):
        msg = "Meine E-Mail ist anna.muster@example.com, danke!"
        match = self.EMAIL_RE.search(msg)
        assert match is not None
        assert match.group().lower() == "anna.muster@example.com"

    def test_no_match_in_plain_text(self):
        msg = "Hallo, ich moechte mein Kind anmelden."
        assert self.EMAIL_RE.search(msg) is None

    def test_extracts_email_with_plus(self):
        msg = "user+tag@example.com"
        match = self.EMAIL_RE.search(msg)
        assert match is not None
        assert "user+tag@example.com" in match.group()


# ---------------------------------------------------------------------------
# 6. Resume token generation format
# ---------------------------------------------------------------------------


class TestResumeTokenFormat:
    def test_generated_token_is_6_chars(self):
        token = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        assert len(token) == 6

    def test_generated_token_valid_chars(self):
        valid_chars = set(string.ascii_uppercase + string.digits)
        for _ in range(20):
            token = "".join(
                secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
            )
            assert all(c in valid_chars for c in token)

    def test_tokens_are_unique(self):
        tokens = set()
        for _ in range(100):
            token = "".join(
                secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
            )
            tokens.add(token)
        # With 36^6 possible tokens, 100 should all be unique
        assert len(tokens) == 100


# ---------------------------------------------------------------------------
# 7. Store persists state with parent_email as key
# ---------------------------------------------------------------------------


class TestStoreParentEmailKey:
    def test_save_uses_parent_email_as_key(self, store):
        state = ConversationState(conversation_id="uuid-123")
        state.parent_email = "anna@example.com"
        store.save(state)

        found = store.find_by_email("anna@example.com")
        assert found is not None
        assert found.conversation_id == "uuid-123"

    def test_save_persists_resume_token(self, store):
        state = ConversationState(conversation_id="anna@example.com")
        state.parent_email = "anna@example.com"
        state.resume_token = "TEST42"
        store.save(state)

        loaded = store.find_by_email("anna@example.com")
        assert loaded is not None
        assert loaded.resume_token == "TEST42"


# ---------------------------------------------------------------------------
# 8. list_incomplete does not include completed sessions
# ---------------------------------------------------------------------------


class TestListIncomplete:
    def test_includes_incomplete_excludes_completed(self, store):
        incomplete = ConversationState(
            conversation_id="inc@example.com",
            parent_email="inc@example.com",
        )
        incomplete.flow_step = "child_name"
        store.save(incomplete)

        complete = ConversationState(
            conversation_id="com@example.com",
            parent_email="com@example.com",
        )
        complete.completed = True
        store.save(complete)

        result = store.list_incomplete()
        ids = [s.conversation_id for s in result]
        assert "inc@example.com" in ids
        assert "com@example.com" not in ids

    def test_list_incomplete_empty_store(self, store):
        assert store.list_incomplete() == []


# ---------------------------------------------------------------------------
# 9. Cross-channel resume — channel field
# ---------------------------------------------------------------------------


class TestCrossChannelResume:
    """Verify that the channel field is persisted and enables cross-channel detection."""

    def test_channel_field_default_is_chat(self):
        state = ConversationState(conversation_id="test")
        assert state.channel == "chat"

    def test_channel_field_round_trip_chat(self):
        state = ConversationState(conversation_id="test")
        state.channel = "chat"
        restored = ConversationState.from_dict(state.to_dict())
        assert restored.channel == "chat"

    def test_channel_field_round_trip_email(self):
        state = ConversationState(conversation_id="test")
        state.channel = "email"
        restored = ConversationState.from_dict(state.to_dict())
        assert restored.channel == "email"

    def test_channel_defaults_to_chat_when_key_missing(self):
        """Older persisted conversations without the channel key deserialise safely."""
        data = {
            "conversation_id": "old@example.com",
            "parent_email": "old@example.com",
            "language": "de",
            "flow_step": "greeting",
            "registration": {},
            "messages": [],
            "completed": False,
            "reminder_count": 0,
            "last_inbound_message_id": "",
            "loop_escalated": False,
            # channel intentionally absent
        }
        state = ConversationState.from_dict(data)
        assert state.channel == "chat"

    def test_email_channel_state_found_by_chat_via_find_by_email(self, store):
        """A session started via email can be found by the chat channel using find_by_email."""
        email_session = ConversationState(
            conversation_id="parent@example.com",
            parent_email="parent@example.com",
        )
        email_session.channel = "email"
        email_session.flow_step = "parent_contact"
        store.save(email_session)

        # Chat channel looks up by email — same store, same key
        found = store.find_by_email("parent@example.com")
        assert found is not None
        assert found.channel == "email"
        assert found.flow_step == "parent_contact"

    def test_chat_channel_state_found_by_email_agent(self, store):
        """A session started via web chat can be found by the email channel."""
        chat_session = ConversationState(
            conversation_id="uuid-chat-123",
            parent_email="parent@example.com",
        )
        chat_session.channel = "chat"
        chat_session.flow_step = "special_needs"
        store.save(chat_session)

        found = store.find_by_email("parent@example.com")
        assert found is not None
        assert found.channel == "chat"
        assert found.flow_step == "special_needs"

    def test_channel_updated_to_email_when_email_agent_takes_over(self, store):
        """When the email agent processes a message for a chat session, channel becomes 'email'."""
        chat_session = ConversationState(
            conversation_id="parent@example.com",
            parent_email="parent@example.com",
        )
        chat_session.channel = "chat"
        chat_session.flow_step = "special_needs"
        store.save(chat_session)

        # Simulate what email agent does: load, set channel to email, save
        loaded = store.load("parent@example.com")
        assert loaded is not None
        assert loaded.channel == "chat"  # was started via chat

        loaded.channel = "email"
        store.save(loaded)

        updated = store.find_by_email("parent@example.com")
        assert updated is not None
        assert updated.channel == "email"

    def test_registration_record_includes_correct_channel(self, store, fresh_state, complete_registration):
        """The completed registration record stores the channel from state."""
        fresh_state.registration = complete_registration
        fresh_state.channel = "chat"
        fresh_state.completed = True
        email_key, version = store.save_registration(fresh_state)

        record = store.get_current_registration(fresh_state.parent_email)
        assert record is not None
        assert record["metadata"]["channel"] == "chat"

    def test_registration_record_stores_email_channel(self, store, fresh_state, complete_registration):
        """A registration completed via email has 'email' in the metadata channel."""
        fresh_state.registration = complete_registration
        fresh_state.channel = "email"
        fresh_state.completed = True
        email_key, version = store.save_registration(fresh_state)

        record = store.get_current_registration(fresh_state.parent_email)
        assert record is not None
        assert record["metadata"]["channel"] == "email"
