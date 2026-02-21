"""IMAP / SMTP email channel adapter.

Handles:
- Polling the inbox for unread messages (IMAP)
- Conversation matching by sender email address (NOT by thread headers)
- Sending reply emails (SMTP) with proper threading headers for email clients
- Stripping quoted reply text so the agent only sees the new content

Threading headers (Message-ID, In-Reply-To, References) are preserved for
outbound replies so messages appear threaded in Gmail/Outlook, but they are
NOT used to identify which conversation an incoming message belongs to.
Conversation matching is exclusively by normalized sender email address.
"""

import email
import email.header
import email.utils
import imaplib
import logging
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decode_header(value: str) -> str:
    """Decode an RFC-2047 encoded email header value."""
    parts = email.header.decode_header(value or "")
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _extract_text(msg: email.message.Message) -> str:
    """Extract the plain-text body from a (potentially multi-part) message."""
    if msg.is_multipart():
        for part in msg.walk():
            if (
                part.get_content_type() == "text/plain"
                and "attachment" not in str(part.get("Content-Disposition", ""))
            ):
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(charset, errors="replace")
    return ""


def _strip_quoted_text(text: str) -> str:
    """Remove quoted reply text from the email body.

    Heuristics:
    - Drop lines starting with ">"
    - Stop at common reply-separator patterns
    """
    lines = text.splitlines()
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        # Common separators used by email clients
        if re.match(r"^-{3,}|^_{3,}|^={3,}", stripped):
            break
        if re.match(r"^On .+ wrote:$", stripped):
            break
        if re.match(r"^Am .+ schrieb .+:$", stripped):  # German Outlook/Thunderbird
            break
        if "-----Original Message-----" in stripped:
            break
        result.append(line)
    return "\n".join(result).strip()


def _generate_message_id(from_addr: str) -> str:
    domain = from_addr.split("@")[-1] if "@" in from_addr else "meister-eder.local"
    return f"<{time.time():.6f}.{id(from_addr)}@{domain}>"


def _build_quoted_block(original_text: str, from_addr: str) -> str:
    """Format original_text as a standard email quote block.

    Produces the classic:

        On <date>, <from> wrote:
        > line 1
        > line 2
    """
    date_str = time.strftime("%a, %d %b %Y %H:%M", time.localtime())
    header = f"Am {date_str} schrieb {from_addr}:"
    quoted_lines = "\n".join(
        f"> {line}" for line in original_text.splitlines()
    )
    return f"\n\n{header}\n{quoted_lines}"


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class EmailChannel:
    """Wraps IMAP polling and SMTP sending for the email conversation channel."""

    def __init__(
        self,
        imap_host: str,
        imap_port: int,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
        use_tls: bool = True,
        registration_email: str = "",
    ) -> None:
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_ssl = use_ssl
        self._use_tls = use_tls
        self._from_email = registration_email or username

    # ------------------------------------------------------------------
    # IMAP — receive
    # ------------------------------------------------------------------

    def fetch_unread_messages(self) -> list[dict]:
        """Poll the inbox and return all unread messages as structured dicts.

        Each dict contains:
            from          — sender email address (use this as conversation key)
            subject       — decoded subject line
            message_id    — Message-ID of this inbound email (for reply threading)
            in_reply_to   — In-Reply-To header (for reply threading, may be empty)
            references    — References header (for reply threading, may be empty)
            body          — stripped plain-text body (quoted text removed)

        Note: ``thread_id`` is no longer returned. Conversation matching is done
        by ``from`` (sender email address), not by threading headers.
        """
        messages: list[dict] = []
        try:
            imap = self._connect_imap()
            imap.select("INBOX")

            _, data = imap.search(None, "UNSEEN")
            msg_nums = data[0].split()

            for num in msg_nums:
                try:
                    _, raw_data = imap.fetch(num, "(RFC822)")
                    raw = raw_data[0][1]
                    msg = email.message_from_bytes(raw)

                    from_addr = email.utils.parseaddr(msg.get("From", ""))[1]
                    subject = _decode_header(msg.get("Subject", "(no subject)"))
                    message_id = msg.get("Message-ID", "").strip()
                    in_reply_to = msg.get("In-Reply-To", "").strip()
                    references = msg.get("References", "").strip()

                    raw_body = _extract_text(msg)
                    body = _strip_quoted_text(raw_body)

                    if not body.strip():
                        imap.store(num, "+FLAGS", "\\Seen")
                        continue

                    messages.append(
                        {
                            "from": from_addr,
                            "subject": subject,
                            "message_id": message_id,
                            "in_reply_to": in_reply_to,
                            "references": references,
                            "body": body,
                            "raw_body": raw_body,
                        }
                    )
                    imap.store(num, "+FLAGS", "\\Seen")

                except Exception:
                    logger.exception("Error processing IMAP message %s", num)

            imap.logout()

        except Exception:
            logger.exception("IMAP connection/fetch error")

        return messages

    # ------------------------------------------------------------------
    # SMTP — send
    # ------------------------------------------------------------------

    def send_reply(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = "",
        references: str = "",
        quoted_text: str = "",
        quoted_from: str = "",
    ) -> str:
        """Send an email reply.

        If quoted_text is provided it is appended to body as a standard
        ``> ``-prefixed quote block so parents can see what they wrote.

        Returns the new Message-ID so the caller can track the thread.
        """
        new_message_id = _generate_message_id(self._from_email)

        # Ensure subject starts with "Re:"
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Build References chain
        ref_parts = [r for r in [references, in_reply_to] if r]
        new_references = " ".join(ref_parts)

        # Append quoted original message
        if quoted_text.strip():
            body = body + _build_quoted_block(quoted_text, quoted_from or to)

        msg = MIMEMultipart("alternative")
        msg["From"] = self._from_email
        msg["To"] = to
        msg["Subject"] = subject
        msg["Message-ID"] = new_message_id
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if new_references:
            msg["References"] = new_references

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if not self._smtp_host:
            logger.warning("SMTP not configured — reply NOT sent to %s: %s", to, subject)
            logger.debug("Reply body:\n%s", body)
            return new_message_id

        try:
            if self._use_tls:
                server = smtplib.SMTP(self._smtp_host, self._smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self._smtp_host, self._smtp_port)

            server.login(self._username, self._password)
            server.sendmail(self._from_email, [to], msg.as_string())
            server.quit()
            logger.info("Reply sent to %s (thread %s)", to, in_reply_to or new_message_id)
        except Exception:
            logger.exception("Failed to send reply to %s", to)

        return new_message_id

    def send_reminder(
        self,
        to: str,
        subject: str,
        body: str,
        in_reply_to: str = "",
        references: str = "",
    ) -> None:
        """Send a reminder email for an incomplete registration."""
        self.send_reply(
            to=to,
            subject=subject,
            body=body,
            in_reply_to=in_reply_to,
            references=references,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _connect_imap(self) -> imaplib.IMAP4:
        if self._use_ssl:
            conn = imaplib.IMAP4_SSL(self._imap_host, self._imap_port)
        else:
            conn = imaplib.IMAP4(self._imap_host, self._imap_port)
        conn.login(self._username, self._password)
        return conn

