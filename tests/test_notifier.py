"""Tests for AdminNotifier helper methods."""

import pytest

from src.notifications.notifier import AdminNotifier
from src.models.registration import RegistrationData, Booking, BookingDay


@pytest.fixture
def notifier():
    return AdminNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="agent@example.com",
        password="secret",
        use_tls=True,
        from_email="agent@example.com",
    )


# ---------------------------------------------------------------------------
# _recipients_for
# ---------------------------------------------------------------------------


class TestRecipientsFor:
    def test_indoor_only_recipients(self, notifier):
        recipients = notifier._recipients_for(["indoor"])
        assert any("andrea" in r.lower() or "sigrist" in r.lower() for r in recipients)

    def test_outdoor_only_recipients(self, notifier):
        recipients = notifier._recipients_for(["outdoor"])
        assert any("baba.laeubli" in r.lower() for r in recipients)

    def test_both_includes_both_leaders(self, notifier):
        recipients = notifier._recipients_for(["indoor", "outdoor"])
        joined = " ".join(recipients).lower()
        assert "andrea.sigrist" in joined
        assert "baba.laeubli" in joined


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
