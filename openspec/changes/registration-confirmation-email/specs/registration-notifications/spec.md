## MODIFIED Requirements

### Requirement: Notify parent on completed registration
The system SHALL send an HTML confirmation email to the parent immediately after a registration is completed and stored.

#### Scenario: Confirmation sent to parent email
- **WHEN** a registration is completed
- **THEN** the system SHALL send a confirmation email to the address in `parentGuardian.email`

#### Scenario: Confirmation sent before or alongside admin notification
- **WHEN** a registration is completed
- **THEN** both the admin notification and the parent confirmation SHALL be dispatched in the same completion event; failure of either SHALL be logged but SHALL NOT block the other or fail the registration

#### Scenario: No confirmation for incomplete registration
- **WHEN** a registration is not yet complete (any required field missing)
- **THEN** no confirmation email SHALL be sent to the parent

---

### Requirement: Confirmation email contains full registration summary
The confirmation email SHALL include a summary of all registration data the parent submitted.

#### Scenario: All required fields present in confirmation
- **WHEN** the confirmation email is sent
- **THEN** it SHALL include child name, date of birth, special needs, selected playgroup type(s), selected days, parent/guardian contact details, and emergency contact

#### Scenario: Monthly fee shown as informational text
- **WHEN** the confirmation email is sent
- **THEN** it SHALL display the calculated monthly subscription fee as informational text (not a payment request)

---

### Requirement: Confirmation email contains payment instructions for registration fee
The confirmation email SHALL include instructions for paying the one-time CHF 80 registration fee.

#### Scenario: IBAN and payee shown as text
- **WHEN** the confirmation email is sent
- **THEN** it SHALL display the payee name, IBAN, and amount in plain text so the parent can pay manually if the QR code is not rendered

#### Scenario: Swiss QR-bill embedded inline
- **WHEN** the confirmation email is sent
- **THEN** it SHALL include a Swiss QR-bill image (per SIX Group standard) embedded inline as a `Content-ID` referenced image within the HTML part
- **AND** the QR-bill SHALL encode: IBAN `CH14 0900 0000 4930 8018 8`, payee Familienverein Fällanden Spielgruppen (Huebwisstrase 5, 8117 Fällanden), amount CHF 80.00, currency CHF, reference type NON

#### Scenario: QR-bill fallback for non-HTML clients
- **WHEN** a parent's email client does not render HTML
- **THEN** the plain-text part SHALL include the IBAN and payee details in full so payment is still possible without the QR code

---

### Requirement: Confirmation email language matches parent's detected language
The confirmation email body SHALL be rendered in the language detected during the conversation.

#### Scenario: German parent receives German confirmation
- **WHEN** the conversation language is `"de"`
- **THEN** the confirmation email body SHALL be in German

#### Scenario: English-speaking parent receives English confirmation
- **WHEN** the conversation language is `"en"`
- **THEN** the confirmation email body SHALL be in English

#### Scenario: Unknown language falls back to German
- **WHEN** the stored language value is not `"de"` or `"en"`
- **THEN** the confirmation email SHALL be sent in German

#### Scenario: QR-bill slip labels are not translated
- **WHEN** the confirmation email is rendered in any language
- **THEN** the Swiss QR-bill payment slip labels SHALL remain in German (per SIX Group standard; the slip is internationally recognisable without translation)

---

### Requirement: Parent's conversation language is persisted in the registration record
The language detected during the parent's conversation SHALL be stored in the completed registration record.

#### Scenario: Language written to registration record
- **WHEN** a registration is stored
- **THEN** the JSON record SHALL include a `metadata.language` field containing the detected language code (`"de"` or `"en"`)

#### Scenario: Language defaults to German when not detected
- **WHEN** no language was explicitly detected during the conversation
- **THEN** `metadata.language` SHALL be `"de"`
