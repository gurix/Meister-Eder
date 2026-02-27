## MODIFIED Requirements

### Requirement: Confirmation email sets Reply-To to admin address

The system SHALL set the `Reply-To` header to the admin email address (`spielgruppen@familien-verein.ch`) on the registration completion confirmation email sent to the parent.

#### Scenario: Parent replies to confirmation email
- **WHEN** the agent sends a registration completion confirmation email to a parent
- **THEN** the email SHALL include a `Reply-To` header set to `spielgruppen@familien-verein.ch`
- **AND** a parent reply SHALL be delivered to the admin, not to the registration system's inbox

#### Scenario: Mid-registration emails are unaffected
- **WHEN** the agent sends a conversational email during an ongoing registration (not the final confirmation)
- **THEN** the email SHALL NOT set `Reply-To` to the admin address
- **AND** parent replies SHALL continue to be routed back to the registration system for processing
