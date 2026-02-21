"""Tests for ConversationStore and storage helpers."""

import json
from pathlib import Path

import pytest

from src.storage.json_store import (
    ConversationStore,
    normalize_email,
    _diff_registrations,
)
from src.models.conversation import ConversationState


# ---------------------------------------------------------------------------
# normalize_email
# ---------------------------------------------------------------------------


class TestNormalizeEmail:
    def test_lowercases(self):
        assert normalize_email("Anna.Muster@Example.COM") == "anna.muster@example.com"

    def test_strips_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_already_normalized(self):
        assert normalize_email("user@example.com") == "user@example.com"


# ---------------------------------------------------------------------------
# _diff_registrations
# ---------------------------------------------------------------------------


class TestDiffRegistrations:
    def test_detects_changed_field(self):
        old = {"child": {"fullName": "Lena"}}
        new = {"child": {"fullName": "Lena Muster"}}
        diff = _diff_registrations(old, new)
        assert "child.fullName" in diff
        assert diff["child.fullName"] == ("Lena", "Lena Muster")

    def test_unchanged_fields_not_included(self):
        old = {"child": {"fullName": "Lena", "dateOfBirth": "2022-01-01"}}
        new = {"child": {"fullName": "Lena", "dateOfBirth": "2022-01-01"}}
        assert _diff_registrations(old, new) == {}

    def test_nested_change_detected(self):
        old = {"parentGuardian": {"email": "old@example.com"}}
        new = {"parentGuardian": {"email": "new@example.com"}}
        diff = _diff_registrations(old, new)
        assert "parentGuardian.email" in diff


# ---------------------------------------------------------------------------
# ConversationStore — CRUD
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path) -> ConversationStore:
    return ConversationStore(tmp_path)


class TestConversationStoreCRUD:
    def test_load_returns_none_for_unknown_email(self, store):
        assert store.load("nobody@example.com") is None

    def test_save_and_load_round_trip(self, store, fresh_state):
        store.save(fresh_state)
        loaded = store.load(fresh_state.parent_email)
        assert loaded is not None
        assert loaded.conversation_id == fresh_state.conversation_id

    def test_save_overwrites_existing(self, store, fresh_state):
        store.save(fresh_state)
        fresh_state.language = "en"
        store.save(fresh_state)
        loaded = store.load(fresh_state.parent_email)
        assert loaded.language == "en"

    def test_delete_removes_conversation(self, store, fresh_state):
        store.save(fresh_state)
        store.delete(fresh_state.parent_email)
        assert store.load(fresh_state.parent_email) is None

    def test_delete_nonexistent_is_silent(self, store):
        store.delete("ghost@example.com")  # should not raise

    def test_list_incomplete_returns_non_completed(self, store, fresh_state):
        store.save(fresh_state)
        incomplete = store.list_incomplete()
        assert any(s.conversation_id == fresh_state.conversation_id for s in incomplete)

    def test_list_incomplete_excludes_completed(self, store, fresh_state):
        fresh_state.completed = True
        store.save(fresh_state)
        incomplete = store.list_incomplete()
        assert all(not s.completed for s in incomplete)

    def test_find_by_email_is_alias_for_load(self, store, fresh_state):
        store.save(fresh_state)
        assert store.find_by_email(fresh_state.parent_email) is not None


# ---------------------------------------------------------------------------
# ConversationStore — registration versioning
# ---------------------------------------------------------------------------


class TestRegistrationVersioning:
    def test_save_registration_creates_version_1(self, store, fresh_state, complete_registration):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        email_key, version = store.save_registration(fresh_state)
        assert version == 1
        # email_key is the filesystem-safe form (@ → _at_)
        assert email_key == "anna.muster_at_example.com"

    def test_save_registration_writes_current_json(self, store, fresh_state, complete_registration, tmp_path):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        email_key, _ = store.save_registration(fresh_state)
        current = tmp_path / "registrations" / email_key / "current.json"
        assert current.exists()

    def test_save_registration_version_increments(self, store, fresh_state, complete_registration):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        store.save_registration(fresh_state)
        _, v2 = store.save_registration_version(
            fresh_state, {"child.fullName": ("Old", "New")}
        )
        assert v2 == 2

    def test_get_current_registration_returns_latest(self, store, fresh_state, complete_registration):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        store.save_registration(fresh_state)
        current = store.get_current_registration(fresh_state.parent_email)
        assert current is not None
        assert current["metadata"]["version"] == 1

    def test_get_registration_history_returns_all_versions(self, store, fresh_state, complete_registration):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        store.save_registration(fresh_state)
        store.save_registration_version(fresh_state, {"child.fullName": ("A", "B")})
        history = store.get_registration_history(fresh_state.parent_email)
        assert len(history) == 2

    def test_list_registrations_includes_saved(self, store, fresh_state, complete_registration):
        fresh_state.registration = complete_registration
        fresh_state.completed = True
        store.save_registration(fresh_state)
        registrations = store.list_registrations()
        assert len(registrations) == 1
