## ADDED Requirements

### Requirement: Automated sender detection
The system SHALL detect whether an inbound email was sent by an automated system rather than a human, before the message is processed by the agent.

#### Scenario: MAILER-DAEMON sender
- **WHEN** an email arrives with a sender local-part of `mailer-daemon`, `postmaster`, `noreply`, `no-reply`, `donotreply`, or `bounce` (case-insensitive)
- **THEN** the system SHALL flag the message as automated with a reason string identifying the sender pattern

#### Scenario: RFC 3834 Auto-Submitted header
- **WHEN** an email contains an `Auto-Submitted` header with any value other than `no`
- **THEN** the system SHALL flag the message as automated, citing the header value in the reason

#### Scenario: Auto-Submitted: no is not automated
- **WHEN** an email contains `Auto-Submitted: no`
- **THEN** the system SHALL NOT flag the message as automated based on this header

#### Scenario: Microsoft Exchange auto-reply suppression
- **WHEN** an email contains an `X-Auto-Response-Suppress` header (any value)
- **THEN** the system SHALL flag the message as automated

#### Scenario: Delivery Status Notification (RFC 3462)
- **WHEN** an email has `Content-Type: multipart/report`
- **THEN** the system SHALL flag the message as automated, as this indicates a machine-generated delivery status or read receipt

#### Scenario: X-Loop header
- **WHEN** an email contains an `X-Loop` header (any value)
- **THEN** the system SHALL flag the message as automated

#### Scenario: Bulk or junk precedence
- **WHEN** an email has a `Precedence` header with value `bulk` or `junk`
- **THEN** the system SHALL flag the message as automated

#### Scenario: Bounce / OOO subject line
- **WHEN** an email subject matches patterns indicating delivery failure or automated response (e.g. "Undelivered Mail", "Mail Delivery Failed", "Out of Office", "Abwesenheitsnotiz", "Automatische Antwort")
- **THEN** the system SHALL flag the message as automated

#### Scenario: Normal parent message
- **WHEN** an email has a normal human sender address and no automated-sender headers
- **THEN** the system SHALL NOT flag the message as automated

### Requirement: Automated messages are never replied to
The system SHALL NOT send any reply to a message flagged as automated.

#### Scenario: Bounce message arrives
- **WHEN** the system receives a message flagged as automated
- **THEN** the system SHALL mark the message as read (IMAP Seen flag)
- **AND** the system SHALL call the agent's automated-message handler
- **AND** the system SHALL NOT send any outbound email reply

### Requirement: Message dict includes automation flag
Every message returned by `fetch_unread_messages()` SHALL include:
- `is_automated` (boolean): whether the message was flagged as automated
- `automated_reason` (string): human-readable reason if flagged, empty string otherwise
