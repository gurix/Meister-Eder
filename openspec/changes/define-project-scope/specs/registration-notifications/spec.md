## ADDED Requirements

### Requirement: Notify admin on completed registration
The system SHALL send an email notification to the admin when a new registration is completed.

#### Scenario: Notification sent
- **WHEN** a parent completes a registration
- **THEN** the admin SHALL receive an email notification

#### Scenario: Notification timing
- **WHEN** a registration is completed
- **THEN** the notification SHALL be sent promptly (within minutes)

### Requirement: Notification contains registration summary
The system SHALL include a summary of the registration in the notification email.

#### Scenario: Summary content
- **WHEN** a notification email is sent
- **THEN** it SHALL include child name, parent contact, requested booking days, and any special needs noted

#### Scenario: Notification links to full record
- **WHEN** the admin views the notification email
- **THEN** it SHALL indicate how to access the full registration record

### Requirement: Notification identifies source channel
The system SHALL indicate in the notification which channel the registration came through.

#### Scenario: Email registration notification
- **WHEN** a registration completed via email triggers a notification
- **THEN** the notification SHALL indicate the registration came via email

#### Scenario: Chat registration notification
- **WHEN** a registration completed via chat triggers a notification
- **THEN** the notification SHALL indicate the registration came via chat

### Requirement: Admin can configure notification preferences
The system SHALL allow the admin to configure notification email address.

#### Scenario: Update notification email
- **WHEN** the admin changes the notification email address
- **THEN** subsequent notifications SHALL be sent to the new address
