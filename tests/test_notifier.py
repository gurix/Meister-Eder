"""Tests for AdminNotifier and notification helper functions."""

import email
from email.header import decode_header

import pytest

from src.notifications.notifier import AdminNotifier
from src.notifications.context import (
    calculate_age,
    calculate_monthly_fee,
    format_types,
    load_strings,
)
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
# notify_parent — parent confirmation email
# ---------------------------------------------------------------------------


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
        """German language produces a German subject line."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_parent(complete_registration, language="de")

        assert "Anmeldebestätigung" in _decoded_subject(captured["msg"])

    def test_notify_parent_english_subject(self, notifier, complete_registration, mocker):
        """English language produces an English subject line."""
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
        """Unsupported language codes fall back to German."""
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

    def test_notify_parent_text_body_contains_iban(self, complete_registration):
        """Plain-text body includes the IBAN so payment is possible without the QR image."""
        strings = load_strings("de")
        from src.notifications.context import build_parent_context
        ctx = build_parent_context(complete_registration, strings, has_qr=False)
        text = render_template("parent_confirmation.txt.j2", ctx)
        assert "CH14" in text

    def test_notify_parent_text_body_english_contains_iban(self, complete_registration):
        """English plain-text body also includes the IBAN."""
        strings = load_strings("en")
        from src.notifications.context import build_parent_context
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
