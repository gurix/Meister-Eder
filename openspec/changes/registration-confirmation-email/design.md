## Context

When a registration is completed, `AdminNotifier.notify_admin()` sends an email to the relevant playgroup leaders. The parent receives nothing — no acknowledgement, no summary, no payment details.

The existing `AdminNotifier` in `src/notifications/notifier.py` handles both new-registration and update notifications to admins. It uses `MIMEMultipart("alternative")` and sends via the configured SMTP server. All the SMTP plumbing already works.

This change adds a parent-facing confirmation email triggered at the same point as the admin notification.

## Goals / Non-Goals

**Goals:**
- Parent receives an HTML confirmation email immediately after registration is stored
- Email contains full registration summary (all 13 fields)
- Email contains payment instructions for the CHF 80 registration fee
- Email contains a Swiss QR-bill (QR code image) embedded inline so the parent can pay via banking app or print

**Non-Goals:**
- Translating the QR-bill slip labels themselves (the SIX Group standard mandates German/French/Italian for the payment slip fields — surrounding email text is translated, but the slip is not)
- Sending a reminder if the parent hasn't paid (payment tracking is out of scope)
- Generating a full PDF invoice (QR code embedded in HTML email is sufficient)
- Sibling discount handling in the QR-bill amount (CHF 80 is always fixed for the registration fee)

## Decisions

### 1. Extend `AdminNotifier` vs. New Class

**Decision**: Add `notify_parent()` to the existing `AdminNotifier` class (renamed conceptually; kept in the same file for now).

**Rationale**: The SMTP plumbing (`_send`, `_smtp_host`, credentials) is already there. A `notify_parent` method reuses all of it. Splitting into a separate class would require duplicating constructor parameters and SMTP setup for no structural benefit at this stage.

**Trade-off**: `AdminNotifier` becomes slightly misnamed. Acceptable — the class handles all outbound notification emails. Rename in a future refactor if needed.

### 2. HTML Email Format

**Decision**: Send `multipart/alternative` with both plain-text and HTML parts. The HTML part is the primary view; plain-text is fallback.

**Rationale**: Matches the existing `_send` method's `MIMEMultipart("alternative")` pattern. HTML is needed to embed the QR-bill image inline.

**QR image embedding**: Use `multipart/related` wrapping the HTML part, with the QR PNG attached as `Content-ID` (`cid:qrbill`). This is the standard approach for inline images that don't appear as attachments.

**Structure:**
```
multipart/mixed
└── multipart/alternative
    ├── text/plain  (fallback)
    └── multipart/related
        ├── text/html  (references cid:qrbill)
        └── image/png  (Content-ID: qrbill, inline)
```

### 3. Swiss QR-Bill Generation

**Decision**: Use the `qrbill` Python library to generate the QR code image.

**Rationale**: `qrbill` implements the Swiss QR-bill standard (SIX Group spec) directly. It accepts IBAN, payee address, amount, and currency, and outputs an SVG or PNG. No external services required.

**Fixed payment data** (hardcoded in the notifier, not in config — this is stable bank data):
- IBAN: `CH14 0900 0000 4930 8018 8`
- Payee: Familienverein Fällanden Spielgruppen, c/o Markus Graf, Huebwisstrase 5, 8117 Fällanden
- Amount: CHF 80.00
- Currency: CHF
- Reference type: NON (no structured reference)

**Output**: PNG bytes, embedded as inline image in HTML email.

**Dependency**: Add `qrbill` to `pyproject.toml` dependencies.

### 4. Language

**Decision**: Add a `language` field to `RegistrationData` (default `"de"`). The agent sets it when it detects the parent's language during conversation. The confirmation email body is rendered in the stored language. The QR-bill slip labels are fixed German/French/Italian per the SIX Group standard and are not translated.

**Supported values**: `"de"` (German, default) and `"en"` (English). Other values fall back to `"de"`.

**Where it lives in the model**: A new `metadata` field on `RegistrationData` (a `Metadata` dataclass) with fields `submitted_at`, `channel`, `conversation_id`, and `language`. This also aligns with the JSON schema in `registration-schema.json` which already defines a `metadata` object with those keys. The `language` field is added to both the Python model and the JSON schema.

**Template strategy**: Two string-template dicts (one per language) for all user-visible strings in the confirmation email. The notifier selects the dict based on `registration.metadata.language`. Admin notifications remain German-only (admins are Swiss German speakers).

**Rationale**: Parents who conversed in English reasonably expect an English confirmation. Storing language in the model (rather than passing it as a parameter) means it's persisted with the registration and available for future use (e.g. update notifications, reminders).

### 5. Trigger Point

**Decision**: Call `notify_parent()` immediately after `notify_admin()` at the same trigger site — wherever `notify_admin` is currently called (in `src/agent/core.py` or equivalent).

**Rationale**: The parent notification is a direct consequence of the same event (registration completed). No separate trigger or queue needed.

**Error isolation**: If the parent email fails, log the error but do not fail the registration or block the admin notification. Both notifications are best-effort.

## Risks / Trade-offs

**`qrbill` library maturity**: Actively maintained, used in production Swiss applications. Risk is low. If the library is unavailable, the QR code can be omitted and the plain IBAN text still enables payment.

**Inline image rendering**: Some email clients block inline images by default (Outlook, some mobile clients). The plain-text fallback and the raw IBAN text in the HTML body ensure the payment info is always readable even if the QR image is blocked.

**SMTP failure for parent email**: Parent notification is non-critical (the registration is already stored). Failure is logged as a warning, not an exception.

**Language detection accuracy**: The agent infers language from conversation content. Misdetection is possible but low-risk — a parent who receives a German email when they expected English can still understand the registration summary. The QR-bill is universally recognisable regardless of surrounding language.

## Open Questions

- Should the confirmation email also include the monthly subscription fee (in addition to the CHF 80 registration fee), or only the registration fee QR-bill? The CHF 80 one-time fee is the immediate action required; the monthly fee is recurring and not yet payable. **Proposed answer: include both as informational text, but the QR-bill is for CHF 80 only.**
- Should the parent's email be CC'd on the admin notification, or kept as a separate send? **Proposed answer: separate send — keeps admin and parent content distinct.**
