"""Tests for AdminNotifier helper methods."""

import email
from email.header import decode_header

import pytest

from src.notifications.notifier import AdminNotifier, _STRINGS_DE, _STRINGS_EN
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
# _format_types
# ---------------------------------------------------------------------------


class TestFormatTypes:
    def test_indoor_label(self, notifier):
        assert "Innen" in notifier._format_types(["indoor"]) or "indoor" in notifier._format_types(["indoor"]).lower()

    def test_outdoor_label(self, notifier):
        assert "Wald" in notifier._format_types(["outdoor"]) or "outdoor" in notifier._format_types(["outdoor"]).lower()

    def test_both_labels(self, notifier):
        result = notifier._format_types(["indoor", "outdoor"])
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _calculate_age
# ---------------------------------------------------------------------------


class TestCalculateAge:
    def test_returns_age_string(self, notifier):
        result = notifier._calculate_age("2022-01-01")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invalid_dob_returns_original_string(self, notifier):
        result = notifier._calculate_age("not-a-date")
        assert result == "not-a-date"


# ---------------------------------------------------------------------------
# _calculate_monthly_fee
# ---------------------------------------------------------------------------


class TestCalculateMonthlyFee:
    def test_indoor_one_day(self, notifier, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[BookingDay(day="monday", type="indoor")],
        )
        fee = notifier._calculate_monthly_fee(complete_registration)
        assert "130" in fee

    def test_indoor_two_days(self, notifier, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[
                BookingDay(day="monday", type="indoor"),
                BookingDay(day="wednesday", type="indoor"),
            ],
        )
        fee = notifier._calculate_monthly_fee(complete_registration)
        assert "260" in fee

    def test_indoor_three_days(self, notifier, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["indoor"],
            selected_days=[
                BookingDay(day="monday", type="indoor"),
                BookingDay(day="wednesday", type="indoor"),
                BookingDay(day="thursday", type="indoor"),
            ],
        )
        fee = notifier._calculate_monthly_fee(complete_registration)
        assert "390" in fee

    def test_outdoor_one_day(self, notifier, complete_registration):
        complete_registration.booking = Booking(
            playgroup_types=["outdoor"],
            selected_days=[BookingDay(day="monday", type="outdoor")],
        )
        fee = notifier._calculate_monthly_fee(complete_registration)
        assert "250" in fee


# ---------------------------------------------------------------------------
# _send — SMTP interaction
# ---------------------------------------------------------------------------


class TestSend:
    def test_send_calls_smtp(self, notifier, mocker):
        # _send uses smtplib.SMTP directly (not as context manager)
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
        recipients = call_args[0][1]  # positional arg: to_addrs
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

    def test_notify_parent_text_body_contains_iban(self, notifier_no_smtp, complete_registration):
        """Plain-text body includes the IBAN so payment is possible without the QR image."""
        text = notifier_no_smtp._build_parent_text(complete_registration, _STRINGS_DE)
        assert "CH14" in text

    def test_notify_parent_text_body_english_contains_iban(
        self, notifier_no_smtp, complete_registration
    ):
        """English plain-text body also includes the IBAN."""
        text = notifier_no_smtp._build_parent_text(complete_registration, _STRINGS_EN)
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
        # PNG files start with the 8-byte signature \x89PNG\r\n\x1a\n
        assert png[:4] == b"\x89PNG"
