## MODIFIED Requirements

### Requirement: Notification email sets Reply-To to parent address

The system SHALL set the `Reply-To` header to the registering parent's email address on all registration notification emails sent to playgroup leaders and the admin.

#### Scenario: Leader replies to notification email
- **WHEN** a registration notification email is sent to a playgroup leader (Andrea Sigrist or Barbara Gross)
- **THEN** the email SHALL include a `Reply-To` header set to the parent's email address (`registration.parentGuardian.email`)
- **AND** a leader reply SHALL be delivered directly to the parent

#### Scenario: Admin (CC) replies to notification email
- **WHEN** Markus Graf replies to a registration notification email (received as CC)
- **THEN** the reply SHALL be delivered directly to the parent's email address

#### Scenario: Reply-To applies to all notification routing types
- **WHEN** a notification is sent for an indoor-only, outdoor-only, or both registration
- **THEN** all recipient copies (To and CC) SHALL have `Reply-To` set to the parent's email address
