## ADDED Requirements

### Requirement: Document lock acquisition

The system SHALL provide an endpoint `POST /api/v1/projects/{project_id}/modules/{module}/lock` to acquire an edit lock.

#### Scenario: Acquire lock successfully

- **WHEN** client requests a lock and no active lock exists
- **THEN** the system creates a lock with user_id, timestamp, and TTL=5 minutes
- **AND** returns 200 with lock information

#### Scenario: Lock conflict

- **WHEN** client requests a lock and an active lock exists (not expired)
- **THEN** the system returns 409 Conflict with current lock holder info

#### Scenario: Force acquire expired lock

- **WHEN** client requests a lock and the existing lock is expired (TTL passed)
- **THEN** the system forcefully acquires the lock for the new user

### Requirement: Document lock release

The system SHALL provide an endpoint `DELETE /api/v1/projects/{project_id}/modules/{module}/lock` to release an edit lock.

#### Scenario: Release lock successfully

- **WHEN** lock holder releases the lock
- **THEN** the system removes the lock
- **AND** processes any queued system additions

### Requirement: Lock heartbeat

The system SHALL support lock renewal via heartbeat.

#### Scenario: Heartbeat renewal

- **WHEN** client sends heartbeat request while holding the lock
- **THEN** the system extends the lock TTL by 5 minutes

### Requirement: System addition queue

When a document is locked, the system SHALL queue any automated additions until the lock is released.

#### Scenario: Queue during lock

- **WHEN** classification wants to add content to a locked document
- **THEN** the content is added to a queue for that module

#### Scenario: Process queue on release

- **WHEN** the lock is released
- **THEN** all queued additions are processed and appended to the document

### Requirement: Lock storage

The system SHALL store lock state in memory with optional persistence.

#### Scenario: Lock persists across server restart (optional)

- **WHEN** server restarts
- **THEN** locks may be lost (acceptable for single-user scenarios)
