"""Admin email notifications — new registrations, updates, and parent confirmations."""

import io
import logging
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import qrcode
import qrcode.constants
from PIL import Image, ImageDraw
from qrbill import QRBill

from ..models.registration import RegistrationData
from .context import (
    QR_CITY,
    QR_IBAN,
    QR_PAYEE,
    QR_PCODE,
    QR_STREET,
    build_admin_new_context,
    build_admin_update_context,
    build_parent_context,
    format_types,
)
from .i18n import get_strings
from .renderer import render_template

logger = logging.getLogger(__name__)


class AdminNotifier:
    """Sends formatted admin notification emails.

    Handles two notification types:
    - New registration completed  → "New Registration: …"
    - Existing registration updated → "Registration Updated: …" (with field diff)

    When *smtp_host* is empty the notifier logs and skips sending (dev mode).
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        from_email: str = "",
        indoor_email: str = "",
        outdoor_email: str = "",
        cc_emails: list[str] | None = None,
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_email = from_email or username
        self._indoor_email = indoor_email
        self._outdoor_email = outdoor_email
        self._cc_emails: list[str] = cc_emails or []
        self._model = model

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def notify_admin(
        self,
        registration: RegistrationData,
        registration_id: str,
        version: int,
        conversation_id: str,
        channel: str,
    ) -> None:
        """Send notification for a newly completed registration (version 1)."""
        types = registration.booking.playgroup_types
        to_addresses = self._recipients_for(types)
        if not to_addresses:
            logger.warning(
                "No leader email configured for types %s — new-registration notification skipped.",
                types,
            )
            return

        subject = (
            f"Neue Anmeldung: {registration.child.full_name} "
            f"– {format_types(types)}"
        )
        ctx = build_admin_new_context(registration, registration_id, version, channel)
        body = render_template("admin_new.txt.j2", ctx)

        self._send(
            to=to_addresses,
            cc=self._cc_emails,
            subject=subject,
            body=body,
            reply_to=registration.parent_guardian.email or "",
        )

    def notify_registration_update(
        self,
        registration: RegistrationData,
        registration_id: str,
        version: int,
        change_summary: dict,
        conversation_id: str,
    ) -> None:
        """Send notification when an existing registration is updated."""
        types = registration.booking.playgroup_types
        to_addresses = self._recipients_for(types)
        if not to_addresses:
            logger.warning(
                "No leader email configured for types %s — update notification skipped.",
                types,
            )
            return

        subject = f"Anmeldung aktualisiert: {registration.child.full_name}"
        ctx = build_admin_update_context(registration, registration_id, version, change_summary)
        body = render_template("admin_update.txt.j2", ctx)

        self._send(
            to=to_addresses,
            cc=self._cc_emails,
            subject=subject,
            body=body,
            reply_to=registration.parent_guardian.email or "",
        )

    def notify_loop_escalation(
        self,
        sender_email: str,
        conversation_id: str,
        reason: str,
        message_count: int,
    ) -> None:
        """Alert the admin that a conversation was stopped due to a loop or automated sender.

        Sent to the CC list (Markus Graf / admin) only — no playgroup leader routing needed.
        """
        if not self._cc_emails:
            logger.warning(
                "No admin CC email configured — loop escalation NOT sent for %s", conversation_id
            )
            return

        subject = f"[WARNUNG] Automatische E-Mail / Endlosschleife erkannt: {sender_email}"
        body = (
            f"Das Anmeldungssystem hat eine Konversation automatisch gestoppt.\n\n"
            f"Absender:        {sender_email}\n"
            f"Konversations-ID: {conversation_id}\n"
            f"Nachrichten:     {message_count}\n"
            f"Grund:           {reason}\n\n"
            f"Es wurde keine weitere Antwort gesendet. Bitte prüfen Sie den Sachverhalt "
            f"manuell und leiten Sie die Konversation bei Bedarf weiter.\n\n"
            f"---\nMeister-Eder Anmeldungssystem"
        )
        self._send(
            to=self._cc_emails,
            cc=[],
            subject=subject,
            body=body,
        )
        logger.info(
            "Loop escalation notification sent to admin for conversation %s (reason: %s)",
            conversation_id,
            reason,
        )

    def notify_parent(
        self,
        registration: RegistrationData,
        language: str = "de",
    ) -> None:
        """Send an HTML confirmation email to the parent with registration summary and QR-bill."""
        parent_email = registration.parent_guardian.email
        if not parent_email:
            logger.warning("No parent email in registration — confirmation not sent.")
            return

        strings = get_strings(language, self._model)

        try:
            qr_png = self._generate_qr_bill_png()
        except Exception:
            logger.exception("Failed to generate QR-bill PNG — omitting image from confirmation")
            qr_png = None

        ctx = build_parent_context(registration, strings, has_qr=qr_png is not None)
        html_body = render_template("parent_confirmation.html.j2", ctx)
        text_body = render_template("parent_confirmation.txt.j2", ctx)
        subject = strings["subject"]

        if not self._smtp_host:
            logger.warning(
                "SMTP not configured — parent confirmation NOT sent. Would have emailed %s: %s",
                parent_email,
                subject,
            )
            logger.debug("Parent confirmation body:\n%s", text_body)
            return

        # MIME structure:
        # multipart/mixed
        # └── multipart/alternative
        #     ├── text/plain  (fallback)
        #     └── multipart/related
        #         ├── text/html  (references cid:qrbill)
        #         └── image/png  (Content-ID: qrbill, inline)
        msg_outer = MIMEMultipart("mixed")
        msg_outer["From"] = self._from_email
        msg_outer["To"] = parent_email
        msg_outer["Subject"] = subject
        if self._cc_emails:
            msg_outer["Reply-To"] = self._cc_emails[0]

        msg_alt = MIMEMultipart("alternative")
        msg_alt.attach(MIMEText(text_body, "plain", "utf-8"))

        if qr_png is not None:
            msg_related = MIMEMultipart("related")
            msg_related.attach(MIMEText(html_body, "html", "utf-8"))
            img_part = MIMEImage(qr_png, "png")
            img_part.add_header("Content-ID", "<qrbill>")
            img_part.add_header("Content-Disposition", "inline", filename="qrbill.png")
            msg_related.attach(img_part)
            msg_alt.attach(msg_related)
        else:
            msg_alt.attach(MIMEText(html_body, "html", "utf-8"))

        msg_outer.attach(msg_alt)

        try:
            if self._use_tls:
                server = smtplib.SMTP(self._smtp_host, self._smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self._smtp_host, self._smtp_port)
            server.login(self._username, self._password)
            server.sendmail(self._from_email, [parent_email], msg_outer.as_string())
            server.quit()
            logger.info("Parent confirmation sent to %s", parent_email)
        except Exception:
            logger.exception("Failed to send parent confirmation to %s", parent_email)

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def _recipients_for(self, types: list[str]) -> list[str]:
        """Return To addresses based on which playgroup types are booked."""
        recipients = []
        if "indoor" in types and self._indoor_email:
            recipients.append(self._indoor_email)
        if "outdoor" in types and self._outdoor_email:
            recipients.append(self._outdoor_email)
        return recipients

    # ------------------------------------------------------------------
    # QR-bill generation
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_qr_bill_png() -> bytes:
        """Generate a Swiss QR-bill payment QR code as a PNG image.

        Uses the fixed registration fee payment data (CHF 80.00).
        The QR code includes the Swiss cross overlay as required by the SIX Group standard.

        Returns:
            PNG image bytes of the QR code.
        """
        bill = QRBill(
            account=QR_IBAN,
            creditor={
                "name": QR_PAYEE,
                "street": QR_STREET,
                "pcode": QR_PCODE,
                "city": QR_CITY,
                "country": "CH",
            },
            amount="80.00",
            currency="CHF",
        )
        payload = bill.qr_data()

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        pil_img: Image.Image = qr.make_image(fill_color="black", back_color="white").get_image()
        pil_img = pil_img.convert("RGB")

        # Overlay Swiss cross in center (SIX Group standard)
        w, h = pil_img.size
        cross_size = max(int(w * 0.15), 20)
        cx, cy = w // 2, h // 2
        half = cross_size // 2
        bar = cross_size // 5
        draw = ImageDraw.Draw(pil_img)
        draw.rectangle([cx - half, cy - half, cx + half, cy + half], fill="white")
        draw.rectangle([cx - bar // 2, cy - half, cx + bar // 2, cy + half], fill="#FF0000")
        draw.rectangle([cx - half, cy - bar // 2, cx + half, cy + bar // 2], fill="#FF0000")

        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        return buf.getvalue()

    # ------------------------------------------------------------------
    # SMTP dispatch
    # ------------------------------------------------------------------

    def _send(
        self,
        to: list[str],
        cc: list[str],
        subject: str,
        body: str,
        reply_to: str = "",
    ) -> None:
        if not self._smtp_host:
            logger.warning(
                "SMTP not configured — notification NOT sent. Would have emailed %s (CC: %s): %s",
                to,
                cc,
                subject,
            )
            logger.debug("Notification body:\n%s", body)
            return

        msg = MIMEMultipart("alternative")
        msg["From"] = self._from_email
        msg["To"] = ", ".join(to)
        msg["CC"] = ", ".join(cc)
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain", "utf-8"))
        all_recipients = to + cc

        try:
            if self._use_tls:
                server = smtplib.SMTP(self._smtp_host, self._smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self._smtp_host, self._smtp_port)

            server.login(self._username, self._password)
            server.sendmail(self._from_email, all_recipients, msg.as_string())
            server.quit()
            logger.info("Notification sent to %s", all_recipients)
        except Exception:
            logger.exception("Failed to send notification to %s", all_recipients)
