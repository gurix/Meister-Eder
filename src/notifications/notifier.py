"""Admin email notifications — new registrations, updates, and parent confirmations."""

import io
import logging
import smtplib
from datetime import date, datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import qrcode
import qrcode.constants
from PIL import Image, ImageDraw
from qrbill import QRBill

from ..models.registration import RegistrationData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bilingual string tables for parent confirmation emails
# ---------------------------------------------------------------------------

_STRINGS_DE: dict = {
    "subject": "Anmeldebestätigung – Spielgruppe Pumuckl",
    "greeting": "Guten Tag {name}",
    "intro": (
        "Deine Anmeldung für die Spielgruppe Pumuckl ist bei uns eingegangen. "
        "Hier ist eine Zusammenfassung:"
    ),
    "child_section": "Angaben zum Kind",
    "child_name": "Name",
    "child_dob": "Geburtsdatum",
    "child_needs": "Besondere Bedürfnisse",
    "booking_section": "Spielgruppen-Buchung",
    "booking_type": "Art",
    "booking_days": "Tage",
    "fees_section": "Kosten",
    "monthly_fee": "Monatlicher Beitrag",
    "reg_fee": "Anmeldegebühr (einmalig, erstes Jahr)",
    "deposit": "Reinigungsdepot Innen (rückerstattbar)",
    "parent_section": "Deine Kontaktdaten",
    "parent_name": "Name",
    "parent_address": "Adresse",
    "parent_phone": "Telefon",
    "parent_email": "E-Mail",
    "emergency_section": "Notfallkontakt",
    "emergency_name": "Name",
    "emergency_phone": "Telefon",
    "payment_section": "Zahlungsinformationen",
    "payment_intro": (
        "Bitte überweise die Anmeldegebühr von <strong>CHF&nbsp;80.00</strong> auf folgendes Konto. "
        "Du kannst den QR-Code mit deiner Banking-App scannen:"
    ),
    "payment_intro_text": (
        "Bitte überweise die Anmeldegebühr von CHF 80.00 auf folgendes Konto:"
    ),
    "iban_label": "IBAN",
    "payee_label": "Empfänger",
    "amount_label": "Betrag",
    "closing": (
        "Bei Fragen stehen wir dir gerne zur Verfügung. "
        "Wir freuen uns auf dein Kind!\n\n"
        "Herzliche Grüsse\n"
        "Spielgruppe Pumuckl"
    ),
    "days": {
        "monday": "Montag",
        "wednesday": "Mittwoch",
        "thursday": "Donnerstag",
    },
    "types": {
        "indoor": "Innenspielgruppe",
        "outdoor": "Waldspielgruppe",
    },
    "none": "Keine",
    "deposit_amount": "CHF 50.00",
    "reg_fee_amount": "CHF 80.00",
}

_STRINGS_EN: dict = {
    "subject": "Registration Confirmation – Spielgruppe Pumuckl",
    "greeting": "Dear {name}",
    "intro": (
        "Your registration with Spielgruppe Pumuckl has been received. "
        "Here is a summary:"
    ),
    "child_section": "Child Details",
    "child_name": "Name",
    "child_dob": "Date of birth",
    "child_needs": "Special needs",
    "booking_section": "Playgroup Booking",
    "booking_type": "Type",
    "booking_days": "Days",
    "fees_section": "Fees",
    "monthly_fee": "Monthly subscription",
    "reg_fee": "Registration fee (one-time, first year)",
    "deposit": "Cleaning deposit – indoor (refundable)",
    "parent_section": "Your Contact Details",
    "parent_name": "Name",
    "parent_address": "Address",
    "parent_phone": "Phone",
    "parent_email": "Email",
    "emergency_section": "Emergency Contact",
    "emergency_name": "Name",
    "emergency_phone": "Phone",
    "payment_section": "Payment Details",
    "payment_intro": (
        "Please transfer the registration fee of <strong>CHF&nbsp;80.00</strong> to the account below. "
        "You can scan the QR code with your banking app:"
    ),
    "payment_intro_text": (
        "Please transfer the registration fee of CHF 80.00 to the following account:"
    ),
    "iban_label": "IBAN",
    "payee_label": "Payee",
    "amount_label": "Amount",
    "closing": (
        "If you have any questions, we are happy to help. "
        "We look forward to welcoming your child!\n\n"
        "Kind regards\n"
        "Spielgruppe Pumuckl"
    ),
    "days": {
        "monday": "Monday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
    },
    "types": {
        "indoor": "Indoor Playgroup",
        "outdoor": "Forest Playgroup",
    },
    "none": "None",
    "deposit_amount": "CHF 50.00",
    "reg_fee_amount": "CHF 80.00",
}

# Fixed Swiss QR-bill payment data (stable bank details — not in config)
_QR_IBAN = "CH14 0900 0000 4930 8018 8"
_QR_PAYEE = "Familienverein Fällanden Spielgruppen"
_QR_STREET = "Huebwisstrase 5"
_QR_PCODE = "8117"
_QR_CITY = "Fällanden"


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
            f"– {self._format_types(types)}"
        )
        body = self._build_new_body(registration, registration_id, version, channel)

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
        body = self._build_update_body(registration, registration_id, version, change_summary)

        self._send(
            to=to_addresses,
            cc=self._cc_emails,
            subject=subject,
            body=body,
            reply_to=registration.parent_guardian.email or "",
        )

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
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_types(types: list[str]) -> str:
        has_indoor = "indoor" in types
        has_outdoor = "outdoor" in types
        if has_indoor and has_outdoor:
            return "Innen- und Waldspielgruppe"
        if has_indoor:
            return "Innenspielgruppe"
        if has_outdoor:
            return "Waldspielgruppe"
        return "Spielgruppe"

    @staticmethod
    def _calculate_age(dob_str: str) -> str:
        try:
            dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            today = date.today()
            years = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            months = (today.month - dob.month) % 12
            return f"{years} Jahre, {months} Monate"
        except Exception:
            return dob_str

    @staticmethod
    def _format_dob(dob_str: str) -> str:
        try:
            return datetime.strptime(dob_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        except Exception:
            return dob_str or ""

    @staticmethod
    def _calculate_monthly_fee(registration: RegistrationData) -> str:
        indoor_days = sum(1 for d in registration.booking.selected_days if d.type == "indoor")
        outdoor_days = sum(1 for d in registration.booking.selected_days if d.type == "outdoor")
        fee = 0
        if indoor_days == 1:
            fee += 130
        elif indoor_days == 2:
            fee += 260
        elif indoor_days >= 3:
            fee += 390
        if outdoor_days >= 1:
            fee += 250
        return f"CHF {fee}.-"

    @staticmethod
    def _format_days(registration: RegistrationData) -> str:
        day_map = {"monday": "Montag", "wednesday": "Mittwoch", "thursday": "Donnerstag"}
        type_map = {"indoor": "Innenspielgruppe", "outdoor": "Waldspielgruppe"}
        return ", ".join(
            f"{day_map.get(d.day, d.day.capitalize())} ({type_map.get(d.type, d.type)})"
            for d in registration.booking.selected_days
        )

    @staticmethod
    def _format_change_summary(change_summary: dict) -> str:
        """Render field changes as a human-readable list."""
        lines = []
        for field_path, values in sorted(change_summary.items()):
            old_val, new_val = values["old"], values["new"]
            lines.append(f"  {field_path}:")
            lines.append(f"    Alt: {old_val}")
            lines.append(f"    Neu: {new_val}")
        return "\n".join(lines) if lines else "  (keine Änderungen erkannt)"

    # ------------------------------------------------------------------
    # Email body builders
    # ------------------------------------------------------------------

    def _build_new_body(
        self,
        registration: RegistrationData,
        registration_id: str,
        version: int,
        channel: str,
    ) -> str:
        now = datetime.utcnow()
        pg = registration.parent_guardian
        ec = registration.emergency_contact
        channel_de = {"email": "E-Mail", "chat": "Chat"}.get(channel.lower(), channel.title())

        return (
            "===============================================\n"
            "NEUE SPIELGRUPPEN-ANMELDUNG\n"
            "===============================================\n"
            "\n"
            f"Eingereicht:     {now.strftime('%d.%m.%Y')} um {now.strftime('%H:%M')} Uhr (UTC)\n"
            f"Kanal:           {channel_de}\n"
            f"Anmelde-ID:      {registration_id}  (Version {version})\n"
            "\n"
            "-----------------------------------------------\n"
            "ANGABEN ZUM KIND\n"
            "-----------------------------------------------\n"
            f"Name:            {registration.child.full_name}\n"
            f"Geburtsdatum:    {self._format_dob(registration.child.date_of_birth or '')} "
            f"(Alter: {self._calculate_age(registration.child.date_of_birth or '')})\n"
            f"Bes. Bedürfnisse: {registration.child.special_needs or 'Keine'}\n"
            "\n"
            "-----------------------------------------------\n"
            "SPIELGRUPPEN-AUSWAHL\n"
            "-----------------------------------------------\n"
            f"Art:             {self._format_types(registration.booking.playgroup_types)}\n"
            f"Tage:            {self._format_days(registration)}\n"
            "\n"
            f"Monatlicher Beitrag: {self._calculate_monthly_fee(registration)}\n"
            "(Zzgl. CHF 80 Anmeldegebühr bei Erstanmeldung)\n"
            "\n"
            "-----------------------------------------------\n"
            "ELTERN / ERZIEHUNGSBERECHTIGTE\n"
            "-----------------------------------------------\n"
            f"Name:            {pg.full_name}\n"
            f"Adresse:         {pg.street_address}\n"
            f"                 {pg.postal_code} {pg.city}\n"
            f"Telefon:         {pg.phone}\n"
            f"E-Mail:          {pg.email}\n"
            "\n"
            "-----------------------------------------------\n"
            "NOTFALLKONTAKT\n"
            "-----------------------------------------------\n"
            f"Name:            {ec.full_name}\n"
            f"Telefon:         {ec.phone}\n"
            "\n"
            "===============================================\n"
            "\n"
            "Diese Anmeldung wurde über den automatischen Anmeldeassistenten eingereicht.\n"
        )

    def _build_update_body(
        self,
        registration: RegistrationData,
        registration_id: str,
        version: int,
        change_summary: dict,
    ) -> str:
        now = datetime.utcnow()
        pg = registration.parent_guardian

        return (
            "===============================================\n"
            "ANMELDUNGS-AKTUALISIERUNG\n"
            "===============================================\n"
            "\n"
            f"Aktualisiert:    {now.strftime('%d.%m.%Y')} um {now.strftime('%H:%M')} Uhr (UTC)\n"
            f"Anmelde-ID:      {registration_id}  (Version {version})\n"
            f"Kind:            {registration.child.full_name}\n"
            f"Eltern-E-Mail:   {pg.email}\n"
            "\n"
            "-----------------------------------------------\n"
            "WAS HAT SICH GEÄNDERT\n"
            "-----------------------------------------------\n"
            f"{self._format_change_summary(change_summary)}\n"
            "\n"
            "-----------------------------------------------\n"
            "AKTUELLE ANMELDUNG (nach Aktualisierung)\n"
            "-----------------------------------------------\n"
            f"Spielgruppe:     {self._format_types(registration.booking.playgroup_types)}\n"
            f"Tage:            {self._format_days(registration)}\n"
            f"Monatl. Beitrag: {self._calculate_monthly_fee(registration)}\n"
            "\n"
            f"Elternteil:      {pg.full_name}\n"
            f"Adresse:         {pg.street_address}, {pg.postal_code} {pg.city}\n"
            f"Telefon:         {pg.phone}\n"
            "\n"
            "===============================================\n"
            "\n"
            "Diese Aktualisierung wurde über den automatischen Anmeldeassistenten eingereicht.\n"
        )

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

    # ------------------------------------------------------------------
    # Parent confirmation email
    # ------------------------------------------------------------------

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

        strings = _STRINGS_EN if language == "en" else _STRINGS_DE

        try:
            qr_png = self._generate_qr_bill_png()
        except Exception:
            logger.exception("Failed to generate QR-bill PNG — omitting image from confirmation")
            qr_png = None

        html_body = self._build_parent_html(registration, strings, has_qr=qr_png is not None)
        text_body = self._build_parent_text(registration, strings)
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

    @staticmethod
    def _generate_qr_bill_png() -> bytes:
        """Generate a Swiss QR-bill payment QR code as a PNG image.

        Uses the fixed registration fee payment data (CHF 80.00).
        The QR code includes the Swiss cross overlay as required by the SIX Group standard.

        Returns:
            PNG image bytes of the QR code.
        """
        bill = QRBill(
            account=_QR_IBAN,
            creditor={
                "name": _QR_PAYEE,
                "street": _QR_STREET,
                "pcode": _QR_PCODE,
                "city": _QR_CITY,
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

    def _build_parent_html(
        self,
        registration: RegistrationData,
        strings: dict,
        has_qr: bool = True,
    ) -> str:
        """Render the HTML body for the parent confirmation email."""
        pg = registration.parent_guardian
        ec = registration.emergency_contact
        ch = registration.child

        parent_name = pg.full_name or pg.email or ""
        greeting = strings["greeting"].format(name=parent_name)
        dob_display = self._format_dob(ch.date_of_birth or "")
        special_needs = ch.special_needs or strings["none"]
        pg_types = self._format_types_bilingual(registration.booking.playgroup_types, strings)
        pg_days = self._format_days_bilingual(registration, strings)
        monthly_fee = self._calculate_monthly_fee(registration)
        has_indoor = "indoor" in registration.booking.playgroup_types

        qr_section = ""
        if has_qr:
            qr_section = (
                '<div style="text-align:center;margin:20px 0;">'
                '<img src="cid:qrbill" alt="Swiss QR-Bill" '
                'style="max-width:380px;width:100%;border:1px solid #e0e0e0;">'
                "</div>"
            )

        deposit_row = ""
        if has_indoor:
            deposit_row = (
                f"<tr><td style='padding:4px 0;color:#666;width:55%;'>{strings['deposit']}</td>"
                f"<td>{strings['deposit_amount']}</td></tr>"
            )

        return f"""<!DOCTYPE html>
<html lang="{'de' if strings is _STRINGS_DE else 'en'}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto;padding:20px;">

<div style="background:#2e7d32;color:white;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="margin:0;font-size:22px;">Spielgruppe Pumuckl</h1>
  <p style="margin:4px 0 0;font-size:13px;opacity:.85;">Familienverein Fällanden</p>
</div>

<div style="background:white;border:1px solid #e0e0e0;border-top:none;padding:24px;border-radius:0 0 8px 8px;">

  <p>{greeting},</p>
  <p>{strings['intro']}</p>

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['child_section']}</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:4px 0;color:#666;width:55%;">{strings['child_name']}</td><td>{ch.full_name or ''}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['child_dob']}</td><td>{dob_display}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['child_needs']}</td><td>{special_needs}</td></tr>
  </table>

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['booking_section']}</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:4px 0;color:#666;width:55%;">{strings['booking_type']}</td><td>{pg_types}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['booking_days']}</td><td>{pg_days}</td></tr>
  </table>

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['fees_section']}</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:4px 0;color:#666;width:55%;">{strings['monthly_fee']}</td><td>{monthly_fee}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['reg_fee']}</td><td>{strings['reg_fee_amount']}</td></tr>
    {deposit_row}
  </table>

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['payment_section']}</h2>
  <p>{strings['payment_intro']}</p>
  <table style="width:100%;border-collapse:collapse;background:#f8f8f8;border-radius:4px;">
    <tr>
      <td style="padding:8px;color:#666;width:40%;border-bottom:1px solid #e0e0e0;">{strings['iban_label']}</td>
      <td style="padding:8px;font-family:monospace;font-weight:bold;border-bottom:1px solid #e0e0e0;">CH14 0900 0000 4930 8018 8</td>
    </tr>
    <tr>
      <td style="padding:8px;color:#666;border-bottom:1px solid #e0e0e0;">{strings['payee_label']}</td>
      <td style="padding:8px;border-bottom:1px solid #e0e0e0;">Familienverein Fällanden Spielgruppen<br>Huebwisstrase 5, 8117 Fällanden</td>
    </tr>
    <tr>
      <td style="padding:8px;color:#666;">{strings['amount_label']}</td>
      <td style="padding:8px;font-weight:bold;">CHF 80.00</td>
    </tr>
  </table>
  {qr_section}

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['parent_section']}</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:4px 0;color:#666;width:55%;">{strings['parent_name']}</td><td>{pg.full_name or ''}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['parent_address']}</td><td>{pg.street_address or ''}, {pg.postal_code or ''} {pg.city or ''}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['parent_phone']}</td><td>{pg.phone or ''}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['parent_email']}</td><td>{pg.email or ''}</td></tr>
  </table>

  <h2 style="color:#2e7d32;border-bottom:2px solid #2e7d32;padding-bottom:4px;font-size:16px;">{strings['emergency_section']}</h2>
  <table style="width:100%;border-collapse:collapse;">
    <tr><td style="padding:4px 0;color:#666;width:55%;">{strings['emergency_name']}</td><td>{ec.full_name or ''}</td></tr>
    <tr><td style="padding:4px 0;color:#666;">{strings['emergency_phone']}</td><td>{ec.phone or ''}</td></tr>
  </table>

  <p style="margin-top:24px;white-space:pre-line;">{strings['closing']}</p>

</div>
</body>
</html>"""

    def _build_parent_text(self, registration: RegistrationData, strings: dict) -> str:
        """Render the plain-text fallback for the parent confirmation email."""
        pg = registration.parent_guardian
        ec = registration.emergency_contact
        ch = registration.child

        parent_name = pg.full_name or pg.email or ""
        greeting = strings["greeting"].format(name=parent_name)
        dob_display = self._format_dob(ch.date_of_birth or "")
        special_needs = ch.special_needs or strings["none"]
        pg_types = self._format_types_bilingual(registration.booking.playgroup_types, strings)
        pg_days = self._format_days_bilingual(registration, strings)
        monthly_fee = self._calculate_monthly_fee(registration)
        has_indoor = "indoor" in registration.booking.playgroup_types

        deposit_line = ""
        if has_indoor:
            deposit_line = f"{strings['deposit']}: {strings['deposit_amount']}\n"

        return (
            f"{greeting},\n\n"
            f"{strings['intro']}\n\n"
            "===============================================\n"
            f"{strings['child_section'].upper()}\n"
            "===============================================\n"
            f"{strings['child_name']}: {ch.full_name or ''}\n"
            f"{strings['child_dob']}: {dob_display}\n"
            f"{strings['child_needs']}: {special_needs}\n"
            "\n"
            "===============================================\n"
            f"{strings['booking_section'].upper()}\n"
            "===============================================\n"
            f"{strings['booking_type']}: {pg_types}\n"
            f"{strings['booking_days']}: {pg_days}\n"
            "\n"
            "===============================================\n"
            f"{strings['fees_section'].upper()}\n"
            "===============================================\n"
            f"{strings['monthly_fee']}: {monthly_fee}\n"
            f"{strings['reg_fee']}: {strings['reg_fee_amount']}\n"
            f"{deposit_line}"
            "\n"
            "===============================================\n"
            f"{strings['payment_section'].upper()}\n"
            "===============================================\n"
            f"{strings['payment_intro_text']}\n\n"
            f"  {strings['iban_label']}: CH14 0900 0000 4930 8018 8\n"
            f"  {strings['payee_label']}: Familienverein Fällanden Spielgruppen\n"
            f"             Huebwisstrase 5, 8117 Fällanden\n"
            f"  {strings['amount_label']}: CHF 80.00\n"
            "\n"
            "===============================================\n"
            f"{strings['parent_section'].upper()}\n"
            "===============================================\n"
            f"{strings['parent_name']}: {pg.full_name or ''}\n"
            f"{strings['parent_address']}: {pg.street_address or ''}, {pg.postal_code or ''} {pg.city or ''}\n"
            f"{strings['parent_phone']}: {pg.phone or ''}\n"
            f"{strings['parent_email']}: {pg.email or ''}\n"
            "\n"
            "===============================================\n"
            f"{strings['emergency_section'].upper()}\n"
            "===============================================\n"
            f"{strings['emergency_name']}: {ec.full_name or ''}\n"
            f"{strings['emergency_phone']}: {ec.phone or ''}\n"
            "\n"
            "-----------------------------------------------\n\n"
            f"{strings['closing']}\n"
        )

    @staticmethod
    def _format_types_bilingual(types: list[str], strings: dict) -> str:
        """Format playgroup types using the language-specific type map."""
        type_map: dict = strings["types"]
        labels = [type_map.get(t, t) for t in types]
        return ", ".join(labels) if labels else ""

    @staticmethod
    def _format_days_bilingual(registration: RegistrationData, strings: dict) -> str:
        """Format selected days using the language-specific day map."""
        day_map: dict = strings["days"]
        type_map: dict = strings["types"]
        return ", ".join(
            f"{day_map.get(d.day, d.day.capitalize())} ({type_map.get(d.type, d.type)})"
            for d in registration.booking.selected_days
        )
