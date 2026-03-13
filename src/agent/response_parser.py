"""Parse and apply LLM JSON responses — shared between email and chat channels."""

import json
import logging
import re

from ..models.conversation import ConversationState
from ..models.registration import BookingDay

logger = logging.getLogger(__name__)


def parse_llm_response(content: str) -> dict:
    """Extract the JSON payload from the LLM's raw output.

    Tries three strategies in order:
    1. Entire content is a fenced code block (```json ... ```)
    2. Entire content is a bare JSON object
    3. JSON object embedded somewhere in the text

    Falls back to wrapping raw text as a ``reply`` if nothing parses.
    """
    text = content.strip()

    fence_match = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse LLM response as JSON — using raw text as reply.")
    return {
        "reply": content,
        "intent": "question",
        "updates": {},
        "next_step": "greeting",
        "registration_complete": False,
        "language": "de",
    }


def apply_updates(state: ConversationState, updates: dict) -> None:
    """Write extracted field values into the RegistrationData on *state*."""
    reg = state.registration

    field_map = {
        "child.fullName": lambda v: setattr(reg.child, "full_name", v),
        "child.dateOfBirth": lambda v: setattr(reg.child, "date_of_birth", v),
        "child.specialNeeds": lambda v: setattr(reg.child, "special_needs", v),
        "parentGuardian.fullName": lambda v: (
            setattr(reg.parent_guardian, "full_name", v),
            setattr(state, "parent_name", v),
        ),
        "parentGuardian.streetAddress": lambda v: setattr(reg.parent_guardian, "street_address", v),
        "parentGuardian.postalCode": lambda v: setattr(reg.parent_guardian, "postal_code", str(v)),
        "parentGuardian.city": lambda v: setattr(reg.parent_guardian, "city", v),
        "parentGuardian.phone": lambda v: setattr(reg.parent_guardian, "phone", v),
        "parentGuardian.email": lambda v: setattr(reg.parent_guardian, "email", v),
        "emergencyContact.fullName": lambda v: setattr(reg.emergency_contact, "full_name", v),
        "emergencyContact.phone": lambda v: setattr(reg.emergency_contact, "phone", v),
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


def fallback_message(language: str) -> str:
    """Return a safe error message in the parent's detected language."""
    if language == "en":
        return (
            "I'm sorry, I'm having a technical issue right now. "
            "Please try again in a moment or contact us directly."
        )
    return (
        "Entschuldigung, ich habe gerade ein technisches Problem. "
        "Bitte versuche es gleich nochmal oder kontaktiere uns direkt."
    )
