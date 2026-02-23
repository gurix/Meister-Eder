"""Tests for AdminNotifier and notification helper functions."""

import email
import json
from email.header import decode_header

import pytest

from src.notifications.notifier import AdminNotifier
from src.notifications.context import (
    calculate_age,
    calculate_monthly_fee,
    format_types,
    build_parent_context,
)
from src.notifications.i18n import get_strings, clear_cache
from src.notifications.renderer import render_template
from src.models.registration import RegistrationData, Booking, BookingDay


def _decoded_subject(msg_str: str) -> str:
    """Parse a raw MIME message string and return the decoded Subject header."""
    msg = email.message_from_string(msg_str)
    raw_subject = msg.get("Subject", "")
    parts = decode_header(raw_subject)
    return "".join(
        chunk.decode(enc or "utf-8") if isinstance(chunk, bytes) else chunk
        for chunk, enc in parts
    )


@pytest.fixture(autouse=True)
def reset_translation_cache():
    """Clear the in-memory translation cache before every test."""
    clear_cache()
    yield
    clear_cache()


@pytest.fixture
def notifier():
    return AdminNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="agent@example.com",
        password="secret",
        use_tls=True,
        from_email="agent@example.com",
        indoor_email="andrea@example.com",
        outdoor_email="barbara@example.com",
        cc_emails=["markus@example.com"],
    )


@pytest.fixture
def notifier_no_smtp():
    """Notifier in dev mode (no SMTP host)."""
    return AdminNotifier(
        smtp_host="",
        smtp_port=587,
        username="",
        password="",
        from_email="agent@example.com",
    )


# ---------------------------------------------------------------------------
# format_types
# ---------------------------------------------------------------------------


class TestFormatTypes:
    def test_indoor_label(self):
        result = format_types(["indoor"])
        assert "Innen" in result or "indoor" in result.lower()

    def test_outdoor_label(self):
        result = format_types(["outdoor"])
        assert "Wald" in result or "outdoor" in result.lower()

    def test_both_labels(self):
        result = format_types(["indoor", "outdoor"])
        assert len(result) > 0


# ---------------------------------------------------------------------------
# calculate_age
# ---------------------------------------------------------------------------


class TestCalculateAge:
    def test_returns_age_string(self):
        result = calculate_age("2022-01-01")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_dob_returns_original_string(self):
        result = calculate_age("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# calculate_monthly_fee
# ---------------------------------------------------------------------------


class TestCalculateMonthlyFee:
    def test_indoor_one_day(self, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[BookingDay(day="monday", type="indoor")],
        )
        fee = calculate_monthly_fee(complete_registration)
        assert "130" in fee

    def test_indoor_two_days(self, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[
                BookingDay(day="monday", type="indoor"),
                BookingDay(day="wednesday", type="indoor"),
            ],
        )
        fee = calculate_monthly_fee(complete_registration)
        assert "260" in fee

    def test_indoor_three_days(self, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[
                BookingDay(day="monday", type="indoor"),
                BookingDay(day="wednesday", type="indoor"),
                BookingDay(day="thursday", type="indoor"),
            ],
        )
        fee = calculate_monthly_fee(complete_registration)
        assert "390" in fee

    def test_outdoor_one_day(self, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["outdoor"],
            selected_days=[BookingDay(day="monday", type="outdoor")],
        )
        fee = calculate_monthly_fee(complete_registration)
        assert "250" in fee


# ---------------------------------------------------------------------------
# _send — SMTP interaction
# ---------------------------------------------------------------------------


class TestSend:
    def test_send_calls_smtp(self, notifier, mocker):
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp_cls.return_value

        notifier._send(
            to=["admin@example.com"],
            cc=["cc@example.com"],
            subject="Test",
            body="Hello",
        )

        mock_server.sendmail.assert_called_once()

    def test_send_includes_all_recipients(self, notifier, mocker):
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp_cls.return_value

        notifier._send(
            to=["a@example.com"],
            cc=["b@example.com"],
            subject="Test",
            body="Hello",
        )

        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert "a@example.com" in recipients
        assert "b@example.com" in recipients


# ---------------------------------------------------------------------------
# get_strings — i18n / LLM translation
# ---------------------------------------------------------------------------


class TestGetStrings:
    def test_german_loads_from_yaml_without_llm(self, mocker):
        """German must never trigger an LLM call."""
        mock_litellm = mocker.patch("litellm.completion")
        strings = get_strings("de", "some-model")
        mock_litellm.assert_not_called()
        assert strings["subject"] == "Anmeldebestätigung – Spielgruppe Pumuckl"

    def test_other_language_calls_llm(self, mocker):
        """Non-German languages should call litellm.completion."""
        german = get_strings("de", "some-model")
        translated = {**german, "subject": "Registration Confirmation – Spielgruppe Pumuckl"}
        mock_litellm = mocker.patch("litellm.completion")
        mock_litellm.return_value.choices[0].message.content = json.dumps(translated)

        result = get_strings("en", "some-model")

        mock_litellm.assert_called_once()
        assert result["subject"] == "Registration Confirmation – Spielgruppe Pumuckl"

    def test_result_is_cached(self, mocker):
        """The LLM is only called once per language per process lifetime."""
        german = get_strings("de", "some-model")
        mock_litellm = mocker.patch("litellm.completion")
        mock_litellm.return_value.choices[0].message.content = json.dumps(german)

        get_strings("fr", "some-model")
        get_strings("fr", "some-model")

        assert mock_litellm.call_count == 1

    def test_llm_failure_falls_back_to_german(self, mocker):
        """If the LLM raises, the German strings are returned silently."""
        mocker.patch("litellm.completion", side_effect=RuntimeError("network error"))

        result = get_strings("it", "some-model")

        assert result["subject"] == "Anmeldebestätigung – Spielgruppe Pumuckl"

    def test_passthrough_keys_not_altered(self, mocker):
        """reg_fee_amount and deposit_amount must survive translation unchanged."""
        german = get_strings("de", "some-model")
        # Return translation that omits passthrough keys (as the LLM would)
        without_passthrough = {k: v for k, v in german.items()
                               if k not in {"reg_fee_amount", "deposit_amount"}}
        mocker.patch("litellm.completion").return_value.choices[0].message.content = (
            json.dumps(without_passthrough)
        )

        result = get_strings("en", "some-model")

        assert result["reg_fee_amount"] == "CHF 80.00"
        assert result["deposit_amount"] == "CHF 50.00"


# ---------------------------------------------------------------------------
# notify_parent — parent confirmation email
# ---------------------------------------------------------------------------


class TestNotifyParent:
    def test_notify_parent_calls_send(self, notifier, complete_registration, mocker):
        """notify_parent dispatches an email to the parent address."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp_cls.return_value

        notifier.notify_parent(complete_registration, language="de")

        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert "anna.muster@example.com" in recipients

    def test_notify_parent_german_subject(self, notifier, complete_registration, mocker):
        """German language produces a German subject line without any LLM call."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_parent(complete_registration, language="de")

        assert "Anmeldebestätigung" in _decoded_subject(captured["msg"])

    def test_notify_parent_english_subject(self, notifier, complete_registration, mocker):
        """English language produces an English subject line via LLM translation."""
        german = get_strings("de", "some-model")
        english = {**german, "subject": "Registration Confirmation – Spielgruppe Pumuckl"}
        mocker.patch("litellm.completion").return_value.choices[0].message.content = (
            json.dumps(english)
        )

        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_parent(complete_registration, language="en")

        assert "Registration Confirmation" in _decoded_subject(captured["msg"])

    def test_notify_parent_unknown_language_falls_back_to_de(
        self, notifier, complete_registration, mocker
    ):
        """When the LLM call fails, the email is sent in German."""
        mocker.patch("litellm.completion", side_effect=RuntimeError("timeout"))

        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_parent(complete_registration, language="fr")

        assert "Anmeldebestätigung" in _decoded_subject(captured["msg"])

    def test_notify_parent_no_smtp_skips_send(
        self, notifier_no_smtp, complete_registration, mocker
    ):
        """When SMTP host is empty, no sendmail call is made."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")

        notifier_no_smtp.notify_parent(complete_registration, language="de")

        mock_smtp_cls.assert_not_called()

    def test_text_body_contains_iban(self, complete_registration):
        """Rendered plain-text body includes the IBAN regardless of language."""
        strings = get_strings("de", "some-model")
        ctx = build_parent_context(complete_registration, strings, has_qr=False)
        text = render_template("parent_confirmation.txt.j2", ctx)
        assert "CH14" in text


# ---------------------------------------------------------------------------
# _generate_qr_bill_png
# ---------------------------------------------------------------------------


class TestGenerateQrBillPng:
    def test_returns_nonempty_bytes(self, notifier):
        """_generate_qr_bill_png returns a non-empty bytes object (PNG)."""
        png = notifier._generate_qr_bill_png()
        assert isinstance(png, bytes)
        assert len(png) > 0

    def test_returns_png_signature(self, notifier):
        """Output starts with the PNG magic bytes."""
        png = notifier._generate_qr_bill_png()
        assert png[:4] == b"\x89PNG"
