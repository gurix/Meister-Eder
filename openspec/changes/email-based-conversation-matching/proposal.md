## Why

The current email agent implementation uses email thread IDs (from `Message-ID`, `In-Reply-To`, `References` headers) to match conversations. This breaks when a parent sends a new email instead of replying to the existing thread—they start a fresh conversation and lose all previously collected registration data.

Parents don't always use "Reply"—they may compose a new email, use a different device, or their email client may not preserve threading headers. The system should recognize them by their email address, not by email client threading behavior.

## What Changes

- **Match conversations by sender email address** instead of thread ID
- **One conversation per email address** — simple, permanent association
- **Remove data expiration** — no 30-day retention limit; conversations persist indefinitely
- **Handle post-completion interactions** — if registration is complete, detect whether the parent is asking a question or requesting updates to their registration
- **Version registration updates** — store changes alongside original data for admin audit trail
- **Notify admin of updates** — when a completed registration is modified, notify admin with change details

### Removed Features
- ~~1-month data retention for email conversations~~
- ~~Day 30 data clearing~~
- ~~"Your registration will expire" warning~~

### Retained Features
- Email reminders for incomplete registrations (Day 3, 10, 25) — still useful to nudge parents

## Capabilities

### Modified Capabilities

- `email-channel`: Change conversation matching from thread ID to sender email address; remove data expiration
- `registration-data-store`: Add versioned storage for registration updates; key conversations by email address
- `registration-notifications`: Add notification type for registration updates (not just new registrations)

### New Capabilities

*None — this modifies existing capabilities*

## Impact

- **Email channel**: Simpler matching logic; more reliable conversation continuity
- **Storage**: Conversations keyed by email address instead of thread ID; registration updates stored as versions
- **Admin workflow**: Admin sees change history when registrations are updated
- **Data retention**: No automatic deletion; conversations persist until manually removed
- **Spec updates**: `conversation-flow.md` timeout/retention section needs updating
