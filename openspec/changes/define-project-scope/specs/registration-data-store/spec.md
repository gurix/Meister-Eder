## ADDED Requirements

### Requirement: Store registrations in structured format
The system SHALL store completed registration data in a structured, machine-readable format (e.g., JSON).

#### Scenario: Registration saved
- **WHEN** a registration is completed
- **THEN** all collected data SHALL be stored in a structured format with consistent field names

#### Scenario: Data structure consistency
- **WHEN** multiple registrations are stored
- **THEN** all records SHALL follow the same schema structure

### Requirement: Registration schema validation
The system SHALL validate registration data against a defined schema before storage.

#### Scenario: Valid registration stored
- **WHEN** a registration with all required fields is submitted
- **THEN** the system SHALL validate and store the registration

#### Scenario: Invalid registration rejected
- **WHEN** a registration with missing or invalid fields is submitted for storage
- **THEN** the system SHALL reject the storage and report the validation errors

### Requirement: Registration data is exportable
The system SHALL allow export of registration data in common formats for further processing.

#### Scenario: Export to CSV
- **WHEN** the admin requests a CSV export
- **THEN** the system SHALL generate a CSV file with all registration records

#### Scenario: Export to JSON
- **WHEN** the admin requests a JSON export
- **THEN** the system SHALL provide registration data in JSON format

### Requirement: Registration records are queryable
The system SHALL allow querying registrations by common criteria.

#### Scenario: Query by date range
- **WHEN** the admin queries registrations within a date range
- **THEN** the system SHALL return matching registration records

#### Scenario: Query by booking day
- **WHEN** the admin queries registrations for a specific booking day
- **THEN** the system SHALL return registrations that include that day

### Requirement: Registration data includes metadata
The system SHALL store metadata alongside registration data including submission timestamp and source channel.

#### Scenario: Timestamp recorded
- **WHEN** a registration is completed
- **THEN** the record SHALL include the submission date and time

#### Scenario: Channel recorded
- **WHEN** a registration is completed via email or chat
- **THEN** the record SHALL indicate which channel was used
