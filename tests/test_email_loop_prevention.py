"""Tests for email loop prevention.

Covers three layers:
- detect_automated_message() — header-based bounce/automated sender detection
- EmailAgent.handle_automated_message() — state tracking, one-shot admin alert
- EmailAgent.process_message() — hard message-count cap (MAX_USER_MESSAGES)
- AdminNotifier.notify_loop_escalation() — escalation email dispatch
"""

import email
import json

import pytest
from unittest.mock import MagicMock, patch

from src.channels.email_channel import detect_automated_message
from src.agent.core import EmailAgent, MAX_USER_MESSAGES
from src.models.conversation import ConversationState, ChatMessage
from src.notifications.notifier import AdminNotifier


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_body(msg_str: str) -> str:
    """Extract the decoded plain-text body from a raw MIME message string."""
    parsed = email.message_from_string(msg_str)
    if parsed.is_multipart():
        for part in parsed.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8")
    payload = parsed.get_payload(decode=True)
    return payload.decode(parsed.get_content_charset() or "utf-8") if payload else ""


def _make_msg(
    from_addr: str = "parent@example.com",
    subject: str = "Hallo",
    extra_headers: dict | None = None,
    content_type: str = "text/plain",
) -> email.message.Message:
    """Build a minimal parsed email.message.Message for testing detect_automated_message."""
    raw = (
        f"From: {from_addr}\r\n"
        f"Subject: {subject}\r\n"
        f"Content-Type: {content_type}\r\n"
    )
    for key, value in (extra_headers or {}).items():
        raw += f"{key}: {value}\r\n"
    raw += "\r\nBody text"
    return email.message_from_string(raw)


def _state_with_n_user_messages(n: int, email_addr: str = "loop@example.com") -> ConversationState:
    """Return a ConversationState that already has *n* user messages in its history."""
    state = ConversationState(
        conversation_id=email_addr,
        parent_email=email_addr,
    )
    for i in range(n):
        state.messages.append(ChatMessage(role="user", content=f"Message {i + 1}"))
        state.messages.append(ChatMessage(role="assistant", content=f"Reply {i + 1}"))
    return state


VALID_LLM_REPLY = json.dumps({
    "reply": "Wie heisst dein Kind?",
    "updates": {},
    "next_step": "child_name",
    "registration_complete": False,
    "language": "de",
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kb():
    kb = MagicMock()
    kb.get_all.return_value = "# FAQ\nSome content."
    return kb


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.load.return_value = None
    store.save_registration.return_value = ("loop@example.com", 1)
    return store


@pytest.fixture
def mock_notifier():
    return MagicMock()


@pytest.fixture
def agent(mock_kb, mock_store, mock_notifier):
    return EmailAgent(
        model="anthropic/claude-opus-4-6",
        kb=mock_kb,
        store=mock_store,
        notifier=mock_notifier,
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


@pytest.fixture
def notifier_no_cc():
    """Notifier without any CC recipients — simulates missing ADMIN_EMAIL_CC."""
    return AdminNotifier(
        smtp_host="smtp.example.com",
        smtp_port=587,
        username="agent@example.com",
        password="secret",
        use_tls=True,
        from_email="agent@example.com",
        cc_emails=[],
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
        cc_emails=["markus@example.com"],
    )


# ---------------------------------------------------------------------------
# detect_automated_message — sender address patterns
# ---------------------------------------------------------------------------


class TestDetectAutomatedMessageBySender:
    def test_mailer_daemon_is_automated(self):
        msg = _make_msg(from_addr="MAILER-DAEMON@tacitus2.sui-inter.net")
        is_auto, reason = detect_automated_message(msg, "MAILER-DAEMON@tacitus2.sui-inter.net")
        assert is_auto is True
        assert reason != ""

    def test_mailer_daemon_lowercase_is_automated(self):
        msg = _make_msg(from_addr="mailer-daemon@example.com")
        is_auto, _ = detect_automated_message(msg, "mailer-daemon@example.com")
        assert is_auto is True

    def test_postmaster_is_automated(self):
        msg = _make_msg(from_addr="postmaster@example.com")
        is_auto, _ = detect_automated_message(msg, "postmaster@example.com")
        assert is_auto is True

    def test_noreply_is_automated(self):
        msg = _make_msg(from_addr="noreply@example.com")
        is_auto, _ = detect_automated_message(msg, "noreply@example.com")
        assert is_auto is True

    def test_no_reply_hyphen_is_automated(self):
        msg = _make_msg(from_addr="no-reply@example.com")
        is_auto, _ = detect_automated_message(msg, "no-reply@example.com")
        assert is_auto is True

    def test_donotreply_is_automated(self):
        msg = _make_msg(from_addr="donotreply@example.com")
        is_auto, _ = detect_automated_message(msg, "donotreply@example.com")
        assert is_auto is True

    def test_bounce_is_automated(self):
        msg = _make_msg(from_addr="bounce@example.com")
        is_auto, _ = detect_automated_message(msg, "bounce@example.com")
        assert is_auto is True

    def test_normal_parent_email_is_not_automated(self):
        msg = _make_msg(from_addr="anna.muster@example.com")
        is_auto, reason = detect_automated_message(msg, "anna.muster@example.com")
        assert is_auto is False
        assert reason == ""

    def test_reason_string_mentions_sender(self):
        msg = _make_msg(from_addr="MAILER-DAEMON@tacitus2.sui-inter.net")
        _, reason = detect_automated_message(msg, "MAILER-DAEMON@tacitus2.sui-inter.net")
        assert "MAILER-DAEMON@tacitus2.sui-inter.net" in reason


# ---------------------------------------------------------------------------
# detect_automated_message — RFC / header signals
# ---------------------------------------------------------------------------


class TestDetectAutomatedMessageByHeaders:
    def test_auto_submitted_auto_replied(self):
        msg = _make_msg(extra_headers={"Auto-Submitted": "auto-replied"})
        is_auto, reason = detect_automated_message(msg, "someone@example.com")
        assert is_auto is True
        assert "auto-replied" in reason

    def test_auto_submitted_auto_generated(self):
        msg = _make_msg(extra_headers={"Auto-Submitted": "auto-generated"})
        is_auto, _ = detect_automated_message(msg, "someone@example.com")
        assert is_auto is True

    def test_auto_submitted_no_is_not_automated(self):
        """Auto-Submitted: no means the message was composed by a human."""
        msg = _make_msg(extra_headers={"Auto-Submitted": "no"})
        is_auto, _ = detect_automated_message(msg, "parent@example.com")
        assert is_auto is False

    def test_x_auto_response_suppress_is_automated(self):
        msg = _make_msg(extra_headers={"X-Auto-Response-Suppress": "All"})
        is_auto, reason = detect_automated_message(msg, "someone@example.com")
        assert is_auto is True
        assert "X-Auto-Response-Suppress" in reason

    def test_multipart_report_content_type_is_automated(self):
        msg = _make_msg(content_type="multipart/report")
        is_auto, reason = detect_automated_message(msg, "system@example.com")
        assert is_auto is True
        assert "multipart/report" in reason

    def test_x_loop_header_is_automated(self):
        msg = _make_msg(extra_headers={"X-Loop": "spielgruppen@familien-verein.ch"})
        is_auto, reason = detect_automated_message(msg, "someone@example.com")
        assert is_auto is True
        assert "X-Loop" in reason

    def test_precedence_bulk_is_automated(self):
        msg = _make_msg(extra_headers={"Precedence": "bulk"})
        is_auto, reason = detect_automated_message(msg, "list@example.com")
        assert is_auto is True
        assert "bulk" in reason

    def test_precedence_junk_is_automated(self):
        msg = _make_msg(extra_headers={"Precedence": "junk"})
        is_auto, _ = detect_automated_message(msg, "spam@example.com")
        assert is_auto is True

    def test_precedence_list_is_not_automated(self):
        """Mailing list messages (Precedence: list) are not considered automated."""
        msg = _make_msg(extra_headers={"Precedence": "list"})
        is_auto, _ = detect_automated_message(msg, "newsletter@example.com")
        assert is_auto is False


# ---------------------------------------------------------------------------
# detect_automated_message — subject heuristics
# ---------------------------------------------------------------------------


class TestDetectAutomatedMessageBySubject:
    def test_undelivered_mail_returned_to_sender(self):
        msg = _make_msg(subject="Undelivered Mail Returned to Sender")
        is_auto, reason = detect_automated_message(msg, "mailer@example.com")
        # Caught by sender pattern first, but subject pattern must also flag it
        # Test that a neutral sender + bounce subject is still flagged
        msg2 = _make_msg(
            from_addr="delivery@isp.example.com",
            subject="Undelivered Mail Returned to Sender",
        )
        is_auto2, _ = detect_automated_message(msg2, "delivery@isp.example.com")
        assert is_auto2 is True

    def test_delivery_failed_subject(self):
        msg = _make_msg(
            from_addr="system@isp.example.com",
            subject="Mail Delivery Failed",
        )
        is_auto, _ = detect_automated_message(msg, "system@isp.example.com")
        assert is_auto is True

    def test_out_of_office_subject(self):
        msg = _make_msg(
            from_addr="colleague@example.com",
            subject="Out of Office: Re: Anmeldung",
        )
        is_auto, _ = detect_automated_message(msg, "colleague@example.com")
        assert is_auto is True

    def test_abwesenheitsnotiz_subject(self):
        msg = _make_msg(
            from_addr="colleague@example.com",
            subject="Abwesenheitsnotiz: Anmeldung",
        )
        is_auto, _ = detect_automated_message(msg, "colleague@example.com")
        assert is_auto is True

    def test_automatische_antwort_subject(self):
        msg = _make_msg(
            from_addr="colleague@example.com",
            subject="Automatische Antwort: Ihre Anfrage",
        )
        is_auto, _ = detect_automated_message(msg, "colleague@example.com")
        assert is_auto is True

    def test_normal_registration_subject_is_not_automated(self):
        msg = _make_msg(
            from_addr="parent@example.com",
            subject="Anmeldung meines Kindes",
        )
        is_auto, _ = detect_automated_message(msg, "parent@example.com")
        assert is_auto is False

    def test_case_insensitive_subject_matching(self):
        msg = _make_msg(
            from_addr="system@isp.example.com",
            subject="UNDELIVERED MAIL RETURNED TO SENDER",
        )
        is_auto, _ = detect_automated_message(msg, "system@isp.example.com")
        assert is_auto is True


# ---------------------------------------------------------------------------
# EmailAgent.handle_automated_message — state and escalation
# ---------------------------------------------------------------------------


class TestHandleAutomatedMessage:
    def test_sets_loop_escalated_on_state(self, agent, mock_store):
        """Calling handle_automated_message marks loop_escalated = True in state."""
        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Undelivered Mail Returned to Sender",
            reason="sender matches automated address pattern",
        )
        saved_state = mock_store.save.call_args[0][0]
        assert saved_state.loop_escalated is True

    def test_calls_notify_loop_escalation(self, agent, mock_notifier):
        """Admin is notified once on the first automated message."""
        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Undelivered Mail Returned to Sender",
            reason="sender matches automated address pattern",
        )
        mock_notifier.notify_loop_escalation.assert_called_once()

    def test_notify_called_with_correct_sender(self, agent, mock_notifier):
        agent.handle_automated_message(
            sender_email="MAILER-DAEMON@tacitus2.sui-inter.net",
            subject="Bounce",
            reason="sender match",
        )
        call_kwargs = mock_notifier.notify_loop_escalation.call_args[1]
        assert call_kwargs["sender_email"] == "MAILER-DAEMON@tacitus2.sui-inter.net"

    def test_creates_new_state_when_none_exists(self, agent, mock_store):
        """When no prior state exists, a new ConversationState is created and saved."""
        mock_store.load.return_value = None

        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Bounce",
            reason="automated sender",
        )

        assert mock_store.save.called
        saved_state = mock_store.save.call_args[0][0]
        assert saved_state.parent_email == "mailer-daemon@tacitus2.sui-inter.net"

    def test_subsequent_automated_message_dropped_silently(self, agent, mock_store, mock_notifier):
        """If loop_escalated is already True, no further notify call is made."""
        existing_state = ConversationState(
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            parent_email="mailer-daemon@tacitus2.sui-inter.net",
        )
        existing_state.loop_escalated = True
        mock_store.load.return_value = existing_state

        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Bounce again",
            reason="automated sender",
        )

        mock_notifier.notify_loop_escalation.assert_not_called()

    def test_state_still_saved_when_already_escalated(self, agent, mock_store, mock_notifier):
        """Even when already escalated, last_activity is updated and state is persisted."""
        existing_state = ConversationState(
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            parent_email="mailer-daemon@tacitus2.sui-inter.net",
        )
        existing_state.loop_escalated = True
        mock_store.load.return_value = existing_state

        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Bounce again",
            reason="automated sender",
        )

        assert mock_store.save.called

    def test_notifier_failure_does_not_propagate(self, agent, mock_store, mock_notifier):
        """A failing notifier must not crash the agent — the state is still saved."""
        mock_notifier.notify_loop_escalation.side_effect = RuntimeError("SMTP error")

        # Should not raise
        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Bounce",
            reason="automated sender",
        )

        assert mock_store.save.called

    def test_inbound_message_id_stored(self, agent, mock_store):
        """The inbound Message-ID is persisted for reply-threading purposes."""
        agent.handle_automated_message(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            subject="Bounce",
            reason="automated sender",
            inbound_message_id="<abc123@tacitus2.sui-inter.net>",
        )
        saved_state = mock_store.save.call_args[0][0]
        assert saved_state.last_inbound_message_id == "<abc123@tacitus2.sui-inter.net>"


# ---------------------------------------------------------------------------
# EmailAgent.process_message — hard message-count cap
# ---------------------------------------------------------------------------


class TestProcessMessageCountCap:
    def test_at_limit_message_still_processed(self, agent, mock_store):
        """A conversation with exactly MAX_USER_MESSAGES messages is still replied to."""
        state = _state_with_n_user_messages(MAX_USER_MESSAGES - 1)
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            reply = agent.process_message("loop@example.com", "Another message")

        assert reply == "Wie heisst dein Kind?"

    def test_over_limit_returns_empty_string(self, agent, mock_store):
        """The 21st user message triggers the cap and returns an empty reply."""
        state = _state_with_n_user_messages(MAX_USER_MESSAGES)
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY) as mock_llm:
            reply = agent.process_message("loop@example.com", "One more message")

        assert reply == ""
        mock_llm.assert_not_called()

    def test_over_limit_sets_loop_escalated(self, agent, mock_store):
        """Hitting the cap marks loop_escalated = True in the persisted state."""
        state = _state_with_n_user_messages(MAX_USER_MESSAGES)
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("loop@example.com", "One more message")

        saved_state = mock_store.save.call_args[0][0]
        assert saved_state.loop_escalated is True

    def test_over_limit_calls_notify_loop_escalation(self, agent, mock_store, mock_notifier):
        """Hitting the cap triggers one admin escalation notification."""
        state = _state_with_n_user_messages(MAX_USER_MESSAGES)
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("loop@example.com", "One more message")

        mock_notifier.notify_loop_escalation.assert_called_once()

    def test_over_limit_no_duplicate_notification_when_already_escalated(
        self, agent, mock_store, mock_notifier
    ):
        """If loop_escalated is already True, no second notification is sent."""
        state = _state_with_n_user_messages(MAX_USER_MESSAGES)
        state.loop_escalated = True
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            agent.process_message("loop@example.com", "Yet another message")

        mock_notifier.notify_loop_escalation.assert_not_called()

    def test_over_limit_notify_failure_does_not_propagate(self, agent, mock_store, mock_notifier):
        """If the notifier raises, the cap still returns '' without crashing."""
        mock_notifier.notify_loop_escalation.side_effect = RuntimeError("SMTP down")
        state = _state_with_n_user_messages(MAX_USER_MESSAGES)
        mock_store.load.return_value = state

        with patch("src.llm.complete", return_value=VALID_LLM_REPLY):
            reply = agent.process_message("loop@example.com", "One more message")

        assert reply == ""

    def test_max_user_messages_constant_is_twenty(self):
        """The agreed-upon limit from the spec is 20 inbound messages."""
        assert MAX_USER_MESSAGES == 20


# ---------------------------------------------------------------------------
# AdminNotifier.notify_loop_escalation — SMTP dispatch
# ---------------------------------------------------------------------------


class TestNotifyLoopEscalation:
    def test_sends_email_to_cc_recipients(self, notifier, mocker):
        """The escalation alert is sent to the admin CC address list."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        mock_server = mock_smtp_cls.return_value

        notifier.notify_loop_escalation(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            reason="sender matches automated address pattern",
            message_count=5,
        )

        mock_server.sendmail.assert_called_once()
        call_args = mock_server.sendmail.call_args
        recipients = call_args[0][1]
        assert "markus@example.com" in recipients

    def test_subject_contains_warnung_tag(self, notifier, mocker):
        """Subject must start with [WARNUNG] for easy filtering in the admin inbox."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_loop_escalation(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            reason="automated sender",
            message_count=3,
        )

        import email as email_mod
        from email.header import decode_header
        parsed = email_mod.message_from_string(captured["msg"])
        raw_subject = parsed.get("Subject", "")
        parts = decode_header(raw_subject)
        subject = "".join(
            chunk.decode(enc or "utf-8") if isinstance(chunk, bytes) else chunk
            for chunk, enc in parts
        )
        assert "[WARNUNG]" in subject

    def test_subject_contains_sender_address(self, notifier, mocker):
        """The sender address appears in the subject for quick identification."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_loop_escalation(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            reason="automated sender",
            message_count=3,
        )

        assert "mailer-daemon@tacitus2.sui-inter.net" in captured["msg"]

    def test_body_contains_reason(self, notifier, mocker):
        """The email body includes the specific detection reason."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_loop_escalation(
            sender_email="test@example.com",
            conversation_id="test@example.com",
            reason="Content-Type: multipart/report (delivery status notification)",
            message_count=7,
        )

        body = _decode_body(captured["msg"])
        assert "multipart/report" in body

    def test_body_contains_message_count(self, notifier, mocker):
        """The email body reports the number of messages exchanged."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")
        captured = {}

        def fake_sendmail(from_, to_, msg_str):
            captured["msg"] = msg_str

        mock_smtp_cls.return_value.sendmail.side_effect = fake_sendmail

        notifier.notify_loop_escalation(
            sender_email="test@example.com",
            conversation_id="test@example.com",
            reason="automated sender",
            message_count=12,
        )

        body = _decode_body(captured["msg"])
        assert "12" in body

    def test_no_cc_emails_skips_smtp(self, notifier_no_cc, mocker):
        """When no admin CC email is configured, no SMTP connection is made."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")

        notifier_no_cc.notify_loop_escalation(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            reason="automated sender",
            message_count=3,
        )

        mock_smtp_cls.assert_not_called()

    def test_no_smtp_host_skips_send(self, notifier_no_smtp, mocker):
        """Dev mode (no SMTP host): email is logged but not dispatched."""
        mock_smtp_cls = mocker.patch("smtplib.SMTP")

        notifier_no_smtp.notify_loop_escalation(
            sender_email="mailer-daemon@tacitus2.sui-inter.net",
            conversation_id="mailer-daemon@tacitus2.sui-inter.net",
            reason="automated sender",
            message_count=3,
        )

        mock_smtp_cls.assert_not_called()
