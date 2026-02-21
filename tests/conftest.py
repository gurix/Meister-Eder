"""Shared pytest fixtures."""

import pytest

from src.models.conversation import ConversationState, ChatMessage
from src.models.registration import (
    RegistrationData,
    ChildInfo,
    ParentGuardian,
    EmergencyContact,
    Booking,
    BookingDay,
)


@pytest.fixture
def complete_registration() -> RegistrationData:
    """A fully populated RegistrationData that passes is_complete()."""
    return RegistrationData(
        child=ChildInfo(
            full_name="Lena Muster",
            date_of_birth="2022-03-15",
            special_needs="None",
        ),
        parent_guardian=ParentGuardian(
            full_name="Anna Muster",
            street_address="Hauptstrasse 1",
            postal_code="8117",
            city="Fällanden",
            phone="044 123 45 67",
            email="anna.muster@example.com",
        ),
        emergency_contact=EmergencyContact(
            full_name="Hans Muster",
            phone="079 123 45 67",
        ),
        booking=Booking(
            playgroup_types=["indoor"],
            selected_days=[BookingDay(day="monday", type="indoor")],
        ),
    )


@pytest.fixture
def fresh_state() -> ConversationState:
    """A brand-new ConversationState for a parent email."""
    return ConversationState(
        conversation_id="anna.muster@example.com",
        parent_email="anna.muster@example.com",
    )


@pytest.fixture
def state_with_messages(fresh_state) -> ConversationState:
    """A ConversationState with a couple of chat turns."""
    fresh_state.messages = [
        ChatMessage(role="user", content="Hallo, ich möchte mein Kind anmelden."),
        ChatMessage(role="assistant", content="Hallo! Wie heisst dein Kind?"),
        ChatMessage(role="user", content="Lena Muster"),
    ]
    return fresh_state
