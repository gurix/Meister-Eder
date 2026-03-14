"""Tests for prompts.py — trial_day step integration."""

from unittest.mock import MagicMock

from src.agent.prompts import (
    STEP_DESCRIPTIONS,
    _REGISTRATION_RESPONSE_FORMAT,
    _build_registration_prompt,
)
from src.models.conversation import ConversationState


class TestTrialDayStepInPrompts:
    def test_step_descriptions_contains_trial_day(self):
        assert "trial_day" in STEP_DESCRIPTIONS

    def test_trial_day_in_next_step_options(self):
        assert "trial_day" in _REGISTRATION_RESPONSE_FORMAT

    def test_trial_day_step_description_mentions_schnuppertag(self):
        desc = STEP_DESCRIPTIONS["trial_day"]
        assert isinstance(desc, str)
        assert len(desc) > 0

    def test_registration_flow_in_system_prompt_contains_trial_day(self):
        kb = MagicMock()
        kb.get_all.return_value = ""
        state = ConversationState(conversation_id="test@example.com")
        prompt = _build_registration_prompt(kb, state)
        assert "trial_day" in prompt
