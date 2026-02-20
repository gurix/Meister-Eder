## MODIFIED Requirements

### Requirement: Conversations keyed by email address
The system SHALL store conversations using the sender's normalized email address as the unique key, replacing thread-ID-based storage.

#### Scenario: Conversation file naming
- **WHEN** storing a conversation for `parent@example.com`
- **THEN** the system SHALL use a filename derived from the email address (e.g., `parent_at_example.com.json`)

#### Scenario: Conversation lookup
- **WHEN** loading a conversation for an incoming email
- **THEN** the system SHALL lookup by normalized sender email address

### Requirement: Registration updates stored as versions
The system SHALL store registration updates as separate versions, preserving the original and all subsequent changes for audit purposes.

#### Scenario: Initial registration stored
- **WHEN** a registration is completed for the first time
- **THEN** the system SHALL store it as version 1 with timestamp

#### Scenario: Registration update creates new version
- **WHEN** a parent requests changes to a completed registration
- **THEN** the system SHALL store the updated data as a new version
- **AND** the system SHALL preserve all previous versions

#### Scenario: Version metadata
- **WHEN** storing a registration version
- **THEN** the version SHALL include: version number, timestamp, and change summary (which fields changed)

### Requirement: Current registration accessible
The system SHALL provide easy access to the current (latest) registration data while preserving version history.

#### Scenario: Retrieve current registration
- **WHEN** the admin or system requests the current registration for an email address
- **THEN** the system SHALL return the most recent version

#### Scenario: Retrieve version history
- **WHEN** the admin requests registration history for an email address
- **THEN** the system SHALL return all versions in chronological order

## ADDED Requirements

### Requirement: Post-completion conversation state
The system SHALL support a "completed" conversation state that allows continued interaction for questions and updates.

#### Scenario: Conversation continues after completion
- **WHEN** a parent sends an email after their registration is complete
- **THEN** the system SHALL load the existing conversation and process the message

#### Scenario: Intent detection for post-completion messages
- **WHEN** processing a message in a completed conversation
- **THEN** the system SHALL detect intent: question, update request, or new child registration
