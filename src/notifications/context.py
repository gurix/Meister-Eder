"""Pure functions for building email context dicts from registration data."""

from datetime import date, datetime
from pathlib import Path

import yaml

from ..models.registration import RegistrationData

# ---------------------------------------------------------------------------
# Swiss QR-bill payment constants (stable bank details — not in config)
# ---------------------------------------------------------------------------

QR_IBAN = "CH14 0900 0000 4930 8018 8"
QR_PAYEE = "Familienverein Fällanden Spielgruppen"
QR_STREET = "Huebwisstrase 5"
QR_PCODE = "8117"
QR_CITY = "Fällanden"

_I18N_DIR = Path(__file__).parent / "i18n"

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------


def load_strings(language: str) -> dict:
    """Load the label/string table for *language* (falls back to German)."""
    locale_file = _I18N_DIR / f"{language}.yaml"
    if not locale_file.exists():
        locale_file = _I18N_DIR / "de.yaml"
    with locale_file.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Formatting helpers (pure functions, no side-effects)
# ---------------------------------------------------------------------------


def format_dob(dob_str: str) -> str:
    """Return DD.MM.YYYY from a YYYY-MM-DD string, or the original on error."""
    try:
        return datetime.strptime(dob_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except Exception:
        return dob_str or ""


def calculate_age(dob_str: str) -> str:
    """Return 'X Jahre, Y Monate' from a YYYY-MM-DD string."""
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


def format_types(types: list[str]) -> str:
    """German label for a list of playgroup type keys (admin emails)."""
    has_indoor = "indoor" in types
    has_outdoor = "outdoor" in types
    if has_indoor and has_outdoor:
        return "Innen- und Waldspielgruppe"
    if has_indoor:
        return "Innenspielgruppe"
    if has_outdoor:
        return "Waldspielgruppe"
    return "Spielgruppe"


def format_types_i18n(types: list[str], strings: dict) -> str:
    """Localised label for playgroup type keys using the supplied string table."""
    type_map: dict = strings["types"]
    labels = [type_map.get(t, t) for t in types]
    return ", ".join(labels) if labels else ""


def format_days(registration: RegistrationData) -> str:
    """German day + type labels for admin emails."""
    day_map = {"monday": "Montag", "wednesday": "Mittwoch", "thursday": "Donnerstag"}
    type_map = {"indoor": "Innenspielgruppe", "outdoor": "Waldspielgruppe"}
    return ", ".join(
        f"{day_map.get(d.day, d.day.capitalize())} ({type_map.get(d.type, d.type)})"
        for d in registration.booking.selected_days
    )


def format_days_i18n(registration: RegistrationData, strings: dict) -> str:
    """Localised day + type labels using the supplied string table."""
    day_map: dict = strings["days"]
    type_map: dict = strings["types"]
    return ", ".join(
        f"{day_map.get(d.day, d.day.capitalize())} ({type_map.get(d.type, d.type)})"
        for d in registration.booking.selected_days
    )


def calculate_monthly_fee(registration: RegistrationData) -> str:
    """Compute the monthly fee string from the booking selection."""
    indoor_days = sum(1 for d in registration.booking.selected_days if d.type == "indoor")
    outdoor_days = sum(1 for d in registration.booking.selected_days if d.type == "outdoor")
    fee = indoor_days * 130 + outdoor_days * 250
    return f"CHF {fee}.-"


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def build_admin_new_context(
    registration: RegistrationData,
    registration_id: str,
    version: int,
    channel: str,
) -> dict:
    """Build the template context for the admin new-registration email."""
    now = datetime.utcnow()
    pg = registration.parent_guardian
    ec = registration.emergency_contact
    ch = registration.child
    channel_de = {"email": "E-Mail", "chat": "Chat"}.get(channel.lower(), channel.title())

    return {
        "submitted_date": now.strftime("%d.%m.%Y"),
        "submitted_time": now.strftime("%H:%M"),
        "channel": channel_de,
        "registration_id": registration_id,
        "version": version,
        "child_name": ch.full_name or "",
        "child_dob": format_dob(ch.date_of_birth or ""),
        "child_age": calculate_age(ch.date_of_birth or ""),
        "child_needs": ch.special_needs or "Keine",
        "playgroup_types": format_types(registration.booking.playgroup_types),
        "days": format_days(registration),
        "monthly_fee": calculate_monthly_fee(registration),
        "parent_name": pg.full_name or "",
        "parent_street": pg.street_address or "",
        "parent_postal_code": pg.postal_code or "",
        "parent_city": pg.city or "",
        "parent_phone": pg.phone or "",
        "parent_email": pg.email or "",
        "emergency_name": ec.full_name or "",
        "emergency_phone": ec.phone or "",
    }


def build_admin_update_context(
    registration: RegistrationData,
    registration_id: str,
    version: int,
    change_summary: dict,
) -> dict:
    """Build the template context for the admin registration-update email."""
    now = datetime.utcnow()
    pg = registration.parent_guardian

    changes = [
        {"field": field_path, "old": values["old"], "new": values["new"]}
        for field_path, values in sorted(change_summary.items())
    ]

    return {
        "updated_date": now.strftime("%d.%m.%Y"),
        "updated_time": now.strftime("%H:%M"),
        "registration_id": registration_id,
        "version": version,
        "child_name": registration.child.full_name or "",
        "parent_email": pg.email or "",
        "changes": changes,
        "playgroup_types": format_types(registration.booking.playgroup_types),
        "days": format_days(registration),
        "monthly_fee": calculate_monthly_fee(registration),
        "parent_name": pg.full_name or "",
        "parent_street": pg.street_address or "",
        "parent_postal_code": pg.postal_code or "",
        "parent_city": pg.city or "",
        "parent_phone": pg.phone or "",
    }


def build_parent_context(
    registration: RegistrationData,
    strings: dict,
    has_qr: bool = True,
) -> dict:
    """Build the template context for the parent confirmation email."""
    pg = registration.parent_guardian
    ec = registration.emergency_contact
    ch = registration.child
    parent_name = pg.full_name or pg.email or ""

    return {
        "lang": "de" if strings.get("none") == "Keine" else "en",
        "strings": strings,
        "greeting": strings["greeting"].format(name=parent_name),
        "child_name": ch.full_name or "",
        "child_dob": format_dob(ch.date_of_birth or ""),
        "child_needs": ch.special_needs or strings["none"],
        "playgroup_types": format_types_i18n(registration.booking.playgroup_types, strings),
        "days": format_days_i18n(registration, strings),
        "monthly_fee": calculate_monthly_fee(registration),
        "has_indoor": "indoor" in registration.booking.playgroup_types,
        "has_qr": has_qr,
        "parent_name": pg.full_name or "",
        "parent_address": pg.street_address or "",
        "parent_postal_code": pg.postal_code or "",
        "parent_city": pg.city or "",
        "parent_phone": pg.phone or "",
        "parent_email": pg.email or "",
        "emergency_name": ec.full_name or "",
        "emergency_phone": ec.phone or "",
        "iban": QR_IBAN,
        "payee": QR_PAYEE,
        "payee_street": QR_STREET,
        "payee_postal_code": QR_PCODE,
        "payee_city": QR_CITY,
    }
