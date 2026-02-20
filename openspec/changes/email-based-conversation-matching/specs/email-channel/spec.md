## MODIFIED Requirements

### Requirement: System identifies conversations by sender email address
The system SHALL identify conversations by the sender's email address, not by email threading headers. Each unique email address corresponds to exactly one conversation.

#### Scenario: New email from unknown address
- **WHEN** an email arrives from an address with no existing conversation
- **THEN** the system SHALL create a new conversation keyed by that email address

#### Scenario: New email from known address (any thread)
- **WHEN** an email arrives from an address with an existing conversation
- **THEN** the system SHALL continue that existing conversation regardless of email threading headers

#### Scenario: Email address normalization
- **WHEN** comparing email addresses for matching
- **THEN** the system SHALL normalize addresses (lowercase, trim whitespace) so that `Maria@Example.com` matches `maria@example.com`

### Requirement: Thread headers used for reply threading only
The system SHALL use email threading headers (`In-Reply-To`, `References`) for outbound replies to maintain proper email client threading, but SHALL NOT use them for conversation matching.

#### Scenario: Reply includes threading headers
- **WHEN** the agent sends a reply email
- **THEN** the reply SHALL include `In-Reply-To` referencing the most recent inbound message ID
- **AND** the reply SHALL include `References` header for the email thread chain

#### Scenario: Threading headers ignored for matching
- **WHEN** an inbound email has threading headers pointing to a different conversation
- **THEN** the system SHALL ignore those headers and match by sender email address only

## REMOVED Requirements

### Requirement: Email data retention and expiration
**Reason**: With email-address-based matching, conversations are permanent records. No automatic expiration needed.
**Migration**: Remove any scheduled cleanup jobs; existing conversations remain accessible indefinitely.

### Requirement: Day 30 data clearing
**Reason**: No longer applicable; data persists indefinitely.
**Migration**: None required.

### Requirement: "Registration will expire" warning
**Reason**: No expiration means no warning needed.
**Migration**: Remove from reminder sequence.
