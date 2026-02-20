## ADDED Requirements

### Requirement: Notify admin on registration updates
The system SHALL send an email notification to the admin when an existing registration is updated, including details of what changed.

#### Scenario: Update notification sent
- **WHEN** a parent updates their completed registration
- **THEN** the admin SHALL receive an email notification

#### Scenario: Update notification content
- **WHEN** sending an update notification
- **THEN** the notification SHALL include:
  - Child name and registration ID
  - What changed (field name, old value → new value)
  - When the change was made
  - Version number (e.g., "Version 2 of 2")

#### Scenario: Update notification routing
- **WHEN** sending an update notification
- **THEN** the notification SHALL be routed to the same recipients as the original registration (based on playgroup type)

### Requirement: Distinguish new vs update notifications
The system SHALL clearly distinguish between new registration notifications and update notifications in the email subject and content.

#### Scenario: New registration subject
- **WHEN** sending a notification for a new registration
- **THEN** the subject SHALL be "New Registration: [Child Name] for [Playgroup Type]"

#### Scenario: Update notification subject
- **WHEN** sending a notification for a registration update
- **THEN** the subject SHALL be "Registration Updated: [Child Name]"

## MODIFIED Requirements

### Requirement: Email reminders for incomplete registrations
The system SHALL send reminder emails for incomplete registrations, but SHALL NOT threaten data deletion since data no longer expires.

#### Scenario: Reminder content without expiration warning
- **WHEN** sending a reminder for an incomplete registration
- **THEN** the reminder SHALL encourage completion but SHALL NOT mention data expiration or deletion

#### Scenario: Reminder schedule unchanged
- **WHEN** an incomplete registration exists
- **THEN** reminders SHALL be sent at Day 3, Day 10, and Day 25 after last activity

#### Scenario: Reminders stop after completion
- **WHEN** a registration is completed
- **THEN** no further reminders SHALL be sent for that conversation
