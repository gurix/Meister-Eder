"""Admin email notifications — new registrations and registration updates."""

import logging
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..models.registration import RegistrationData

logger = logging.getLogger(__name__)

# Notification routing per spec
_INDOOR_EMAIL = "andrea.sigrist@gmx.net"
_OUTDOOR_EMAIL = "baba.laeubli@gmail.com"
_ADMIN_CC_EMAIL = "spielgruppen@familien-verein.ch"


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
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._from_email = from_email or username

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

        subject = (
            f"Neue Anmeldung: {registration.child.full_name} "
            f"– {self._format_types(types)}"
        )
        body = self._build_new_body(registration, registration_id, version, channel)

        self._send(
            to=to_addresses,
            cc=[_ADMIN_CC_EMAIL],
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

        subject = f"Anmeldung aktualisiert: {registration.child.full_name}"
        body = self._build_update_body(registration, registration_id, version, change_summary)

        self._send(
            to=to_addresses,
            cc=[_ADMIN_CC_EMAIL],
            subject=subject,
            body=body,
            reply_to=registration.parent_guardian.email or "",
        )

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recipients_for(types: list[str]) -> list[str]:
        recipients = []
        if "indoor" in types:
            recipients.append(_INDOOR_EMAIL)
        if "outdoor" in types:
            recipients.append(_OUTDOOR_EMAIL)
        return recipients

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
