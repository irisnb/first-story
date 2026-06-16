## ADDED Requirements

### Requirement: Event log service appends events to JSONL file

The system SHALL provide an event log service that appends `SystemEvent` entries to a JSONL file.

Each event MUST be written as a single JSON line with:
- `event_id`: Globally unique identifier (UUIDv7 or ULID)
- `idempotency_key`: Stable deduplication key
- `seq`: Monotonically increasing sequence number assigned by the service
- `timestamp`: ISO 8601 formatted wall-clock time
- `type`: Domain-named event type (e.g., `character.created`, `fact.created`)
- `schema_version`: Schema version string
- `payload`: Event-specific data
- `base_state_version`: State version observed by the producer
- `actor`: Origin of the event
- `batch_id`: Optional batch identifier for multi-event operations

The event log file MUST be stored at `events/00001.jsonl` within the project directory.

#### Scenario: Event is appended to empty log

- **WHEN** a new event is appended to an empty event log
- **THEN** the event is written with `seq` equal to 1
- **AND** the JSONL file contains exactly one line

#### Scenario: Event is appended to existing log

- **WHEN** a new event is appended to an existing event log
- **THEN** the event is written with `seq` equal to previous max + 1
- **AND** previous events remain unchanged

### Requirement: Event log service enforces idempotency

The system MUST reject duplicate events based on `idempotency_key`.

If an event with the same `idempotency_key` already exists in the log, the service MUST:
- Return the existing event's `seq`
- NOT append a duplicate entry
- NOT modify the projection

#### Scenario: Duplicate event is rejected

- **WHEN** an event is submitted with an `idempotency_key` that already exists in the log
- **THEN** the service returns the existing event's `seq`
- **AND** no duplicate is written to the log

#### Scenario: Retry with same idempotency_key but different event_id

- **WHEN** an event is submitted with a new `event_id` but same `idempotency_key` as an existing event
- **THEN** the service treats it as a duplicate
- **AND** returns the existing event's `seq`

### Requirement: Event log service supports batch operations

The system MUST support batch events with `batch_id` metadata.

A batch is considered complete when a `batch.committed` event is appended with matching `batch_id`.

Partial batches (events without `batch.committed`) MUST be identifiable during projection rebuild.

#### Scenario: Batch events are written with batch_id

- **WHEN** multiple events are appended with the same `batch_id`
- **THEN** each event contains the `batch_id` field
- **AND** a `batch.committed` event can be appended to mark completion

#### Scenario: Incomplete batch is detectable

- **WHEN** the event log contains events with a `batch_id` but no `batch.committed` event
- **THEN** the projection rebuild can identify the batch as incomplete

### Requirement: Event log service reads events by sequence

The system MUST provide the ability to read events from the log in `seq` order.

Read operations MUST support:
- Reading all events from the beginning
- Reading events from a specific `seq`
- Reading events up to a specific `seq`

#### Scenario: Read all events

- **WHEN** all events are requested from the event log
- **THEN** events are returned in ascending `seq` order
- **AND** all events from the log are included

#### Scenario: Read events from specific seq

- **WHEN** events are requested from `seq` 10
- **THEN** events with `seq` >= 10 are returned
- **AND** events are returned in ascending `seq` order

### Requirement: Event log service builds idempotency index on startup

The system SHALL build an in-memory index of `idempotency_key → seq` on startup.

The index MUST be rebuilt by scanning the event log file.

#### Scenario: Index is built on startup

- **WHEN** the event log service is initialized
- **THEN** an in-memory index is built from existing events
- **AND** subsequent idempotency checks use the index
