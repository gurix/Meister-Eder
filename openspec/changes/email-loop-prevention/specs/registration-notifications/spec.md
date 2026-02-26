## ADDED Requirements

### Requirement: Loop escalation alert to admin
The system SHALL send a plain-text warning email to the admin when a conversation is stopped due to an automated sender or message-count cap breach.

#### Scenario: First automated message from a sender
- **WHEN** the first automated/bounce message is received from a sender address
- **THEN** the system SHALL send one alert email to the admin CC address list
- **AND** the subject SHALL begin with `[WARNUNG]` for easy inbox filtering
- **AND** the subject SHALL include the sender's email address
- **AND** the body SHALL include: sender address, conversation ID, detection reason, and message count
- **AND** no further alert SHALL be sent for subsequent automated messages from the same sender

#### Scenario: Conversation exceeds message-count cap
- **WHEN** a conversation accumulates more than 20 inbound user messages without completing
- **THEN** the system SHALL send one alert email to the admin CC address list on first breach
- **AND** the body SHALL identify the conversation and state that the message limit was exceeded
- **AND** no further alert SHALL be sent for subsequent messages in the same capped conversation

#### Scenario: No admin CC address configured
- **WHEN** `ADMIN_EMAIL_CC` is not set and a loop escalation is triggered
- **THEN** the system SHALL log a warning
- **AND** the system SHALL NOT attempt an SMTP connection

#### Scenario: No SMTP host configured (dev mode)
- **WHEN** `SMTP_HOST` is not set and a loop escalation is triggered
- **THEN** the system SHALL log the notification content
- **AND** the system SHALL NOT attempt an SMTP connection

### Requirement: Alert routing
Loop escalation alerts SHALL be sent only to the admin CC list (`ADMIN_EMAIL_CC`). They SHALL NOT be sent to playgroup leaders (Andrea Sigrist, Barbara Gross), as loop detection is an operational concern, not a registration event.
