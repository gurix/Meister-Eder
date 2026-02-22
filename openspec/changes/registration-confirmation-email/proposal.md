## Why

When a parent completes registration, they currently receive no confirmation. They have no record of what they submitted, no clarity on next steps, and no way to pay the registration fee without separately asking for bank details. This creates uncertainty for parents and additional back-and-forth for admins.

A confirmation email closes this gap: the parent gets a clear summary of their registration, knows exactly what they agreed to, and can pay immediately using the included Swiss QR-bill.

## What Changes

- **Send HTML confirmation email to the parent** immediately when a registration is completed and stored
- **Include full registration summary** — all fields the parent filled out, formatted clearly
- **Include payment instructions** (German text) for the CHF 80 registration fee with IBAN and payee details
- **Include a Swiss QR-bill** (payment QR code) so the parent can pay directly from their banking app or print-to-pay
- The confirmation is sent in the **same language** the parent used during the conversation (German or English), but the QR-bill and payment block are always in German (banking standard)

## Capabilities

### Modified Capabilities

- `registration-notifications`: Currently only notifies admins. Extended to also send a confirmation to the parent's email address upon completion.

### New Capabilities

*None — this extends an existing capability*

## Impact

- **Parents**: Receive immediate, clear confirmation with everything they need — what was registered and how to pay. No need to ask for bank details.
- **Admins**: Fewer follow-up inquiries about "did my registration go through?" and "where do I pay?". Payment is initiated earlier.
- **Email deliverability**: System must send to parent email, not just admin addresses. Parent email is already a required field in the registration schema.
- **Swiss QR-bill generation**: Requires a library to generate the QR code image from the payment data (IBAN, amount, payee address). The QR code is embedded inline in the HTML email.
- **Bilingual**: Confirmation body adapts to the parent's language. The payment section uses German regardless (Swiss QR-bill standard).
