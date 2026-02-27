## Why

The system sends two distinct types of emails to different audiences with different needs for follow-up communication. Currently, the Reply-To behavior for these emails is either unspecified or inconsistent:

1. **Confirmation emails to parents** — sent by the agent after registration is complete. If a parent replies to this email, that reply should reach the admin (Markus Graf), not bounce back into the agent's inbox for further automated processing.

2. **Registration notification emails to playgroup leaders/admins** — sent to Andrea Sigrist, Barbara Gross, and Markus Graf when a new registration is submitted. If an admin wants to follow up with the parent directly, their reply must go to the parent's email, not back to the registration system.

Without explicit Reply-To configuration, email clients will default to replying to the From address (the registration system's email). This creates confusion: parent replies to confirmation emails enter the agent pipeline instead of reaching a human admin, and admin replies to notification emails go to the registration inbox rather than the parent.

## What Changes

- **Confirmation emails**: Add a `Reply-To` header set to the admin email address (`spielgruppen@familien-verein.ch`) so parent replies reach a human directly
- **Admin notification emails**: Confirm and formally specify that `Reply-To` is set to the parent's email address so admins can respond to parents directly from their email client

## Capabilities

### Modified Capabilities

- `email-channel`: Add Reply-To specification for confirmation emails sent to parents after registration completion
- `registration-notifications`: Formally specify Reply-To for admin notification emails (parent's email address)
