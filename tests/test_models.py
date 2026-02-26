"""Tests for data models: RegistrationData and ConversationState."""

import pytest

from src.models.registration import (
    RegistrationData,
    ChildInfo,
    ParentGuardian,
    EmergencyContact,
    Booking,
    BookingDay,
)
from src.models.conversation import ConversationState, ChatMessage


# ---------------------------------------------------------------------------
# RegistrationData.is_complete()
# ---------------------------------------------------------------------------


class TestRegistrationDataIsComplete:
    def test_complete_registration_passes(self, complete_registration):
        assert complete_registration.is_complete() is True

    def test_empty_registration_fails(self):
        assert RegistrationData().is_complete() is False

    def test_missing_child_name_fails(self, complete_registration):
        complete_registration.child.full_name = None
        assert complete_registration.is_complete() is False

    def test_missing_dob_fails(self, complete_registration):
        complete_registration.child.date_of_birth = None
        assert complete_registration.is_complete() is False

    def test_missing_special_needs_fails(self, complete_registration):
        complete_registration.child.special_needs = None
        assert complete_registration.is_complete() is False

    def test_missing_parent_name_fails(self, complete_registration):
        complete_registration.parent_guardian.full_name = None
        assert complete_registration.is_complete() is False

    def test_missing_parent_email_fails(self, complete_registration):
        complete_registration.parent_guardian.email = None
        assert complete_registration.is_complete() is False

    def test_missing_emergency_contact_fails(self, complete_registration):
        complete_registration.emergency_contact.full_name = None
        assert complete_registration.is_complete() is False

    def test_missing_booking_days_fails(self, complete_registration):
        complete_registration.booking.selected_days = []
        assert complete_registration.is_complete() is False

    def test_missing_playgroup_types_fails(self, complete_registration):
        complete_registration.booking.playgroup_types = []
        assert complete_registration.is_complete() is False


# ---------------------------------------------------------------------------
# RegistrationData serialisation round-trip
# ---------------------------------------------------------------------------


class TestRegistrationDataSerialization:
    def test_to_dict_contains_expected_keys(self, complete_registration):
        d = complete_registration.to_dict()
        assert "child" in d
        assert "parentGuardian" in d
        assert "emergencyContact" in d
        assert "booking" in d

    def test_to_dict_child_fields(self, complete_registration):
        d = complete_registration.to_dict()
        assert d["child"]["fullName"] == "Lena Muster"
        assert d["child"]["dateOfBirth"] == "2022-03-15"
        assert d["child"]["specialNeeds"] == "None"

    def test_to_dict_parent_fields(self, complete_registration):
        d = complete_registration.to_dict()
        assert d["parentGuardian"]["email"] == "anna.muster@example.com"
        assert d["parentGuardian"]["postalCode"] == "8117"

    def test_to_dict_booking_fields(self, complete_registration):
        d = complete_registration.to_dict()
        assert d["booking"]["playgroupTypes"] == ["indoor"]
        assert d["booking"]["selectedDays"] == [{"day": "monday", "type": "indoor"}]

    def test_from_dict_round_trip(self, complete_registration):
        d = complete_registration.to_dict()
        restored = RegistrationData.from_dict(d)
        assert restored.child.full_name == complete_registration.child.full_name
        assert restored.parent_guardian.email == complete_registration.parent_guardian.email
        assert restored.emergency_contact.phone == complete_registration.emergency_contact.phone
        assert len(restored.booking.selected_days) == len(complete_registration.booking.selected_days)

    def test_from_dict_outdoor_booking(self):
        data = {
            "child": {"fullName": "Tim", "dateOfBirth": "2021-01-01", "specialNeeds": "None"},
            "parentGuardian": {
                "fullName": "Eva", "streetAddress": "Seeweg 2", "postalCode": "8117",
                "city": "Fällanden", "phone": "044 000 00 00", "email": "eva@example.com",
            },
            "emergencyContact": {"fullName": "Bob", "phone": "079 000 00 00"},
            "booking": {
                "playgroupTypes": ["outdoor"],
                "selectedDays": [{"day": "monday", "type": "outdoor"}],
            },
        }
        reg = RegistrationData.from_dict(data)
        assert reg.booking.playgroup_types == ["outdoor"]
        assert reg.booking.selected_days[0].day == "monday"


# ---------------------------------------------------------------------------
# ConversationState serialisation round-trip
# ---------------------------------------------------------------------------


class TestConversationStateSerialization:
    def test_to_dict_contains_expected_keys(self, fresh_state):
        d = fresh_state.to_dict()
        assert "conversation_id" in d
        assert "language" in d
        assert "flow_step" in d
        assert "messages" in d
        assert "completed" in d

    def test_default_language_is_german(self, fresh_state):
        assert fresh_state.language == "de"

    def test_default_flow_step_is_greeting(self, fresh_state):
        assert fresh_state.flow_step == "greeting"

    def test_default_completed_is_false(self, fresh_state):
        assert fresh_state.completed is False

    def test_from_dict_round_trip(self, state_with_messages):
        state_with_messages.language = "en"
        state_with_messages.flow_step = "parent_name"
        d = state_with_messages.to_dict()
        restored = ConversationState.from_dict(d)
        assert restored.conversation_id == state_with_messages.conversation_id
        assert restored.language == "en"
        assert restored.flow_step == "parent_name"
        assert len(restored.messages) == len(state_with_messages.messages)

    def test_messages_serialized_with_role_and_content(self, state_with_messages):
        d = state_with_messages.to_dict()
        assert d["messages"][0]["role"] == "user"
        assert "Hallo" in d["messages"][0]["content"]


# ---------------------------------------------------------------------------
# ConversationState — loop_escalated field
# ---------------------------------------------------------------------------


class TestConversationStateLoopEscalated:
    def test_default_loop_escalated_is_false(self, fresh_state):
        assert fresh_state.loop_escalated is False

    def test_to_dict_includes_loop_escalated(self, fresh_state):
        d = fresh_state.to_dict()
        assert "loop_escalated" in d
        assert d["loop_escalated"] is False

    def test_to_dict_reflects_true_when_set(self, fresh_state):
        fresh_state.loop_escalated = True
        d = fresh_state.to_dict()
        assert d["loop_escalated"] is True

    def test_from_dict_restores_loop_escalated_true(self, fresh_state):
        fresh_state.loop_escalated = True
        restored = ConversationState.from_dict(fresh_state.to_dict())
        assert restored.loop_escalated is True

    def test_from_dict_defaults_to_false_when_key_missing(self):
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
            # loop_escalated intentionally absent
        }
        state = ConversationState.from_dict(data)
        assert state.loop_escalated is False
