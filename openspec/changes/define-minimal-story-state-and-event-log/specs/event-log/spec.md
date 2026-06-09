## ADDED Requirements

### Requirement: Append-only system event log
The system SHALL use an append-only event log as the source of truth for story state mutations.

Each accepted log entry MUST be a `SystemEvent` with at least:
- `event_id`: globally unique idempotency key.
- `seq`: monotonically increasing log sequence assigned by the Hub/runtime.
- `timestamp`: wall-clock write time.
- `type`: machine-readable mutation type.
- `payload`: mutation-specific structured data.
- `base_state_version`: state version observed when the event was proposed.
- `actor`: origin of the event, such as user, Dialogue Gateway, Extraction Agent, or Hub.

The system MUST NOT mutate or delete accepted log entries during normal operation.

#### Scenario: Accepted event is appended
- **WHEN** the Hub accepts a new `SystemEvent` with a unique `event_id`
- **THEN** the system appends it to the event log with a new `seq`
- **AND** the system preserves all previously accepted events unchanged

#### Scenario: Accepted event remains auditable
- **WHEN** an accepted `SystemEvent` contributes to the current story projection
- **THEN** the system can identify the event by `event_id` and `seq`
- **AND** the system can inspect the original `payload` without re-running an LLM

### Requirement: Idempotent event acceptance
The system MUST use `event_id` as the idempotency key for event acceptance.

A repeated event with the same `event_id` MUST NOT create duplicate log entries or duplicate projection changes.

#### Scenario: Duplicate event is received
- **WHEN** the Hub receives a `SystemEvent` whose `event_id` already exists in the event log
- **THEN** the system does not append a second log entry
- **AND** the resulting projection remains unchanged by the duplicate submission

### Requirement: Base state version is recorded
Every accepted `SystemEvent` MUST record the `base_state_version` observed by the producer when the event was proposed.

The system MUST preserve `base_state_version` for conflict detection, recovery, and future branch/version semantics.

#### Scenario: Event records producer context
- **WHEN** an Agent proposes a mutation based on story state version `42`
- **THEN** the accepted `SystemEvent` records `base_state_version` as `42`

### Requirement: Projection is rebuilt from event log
The system SHALL treat `story_state.json` as a rebuildable current projection, not as the source of truth.

The system MUST be able to reconstruct the current story state by replaying accepted `SystemEvent` entries in `seq` order.

#### Scenario: Projection is lost
- **WHEN** `story_state.json` is missing or corrupted
- **THEN** the system can rebuild an equivalent current projection by replaying the event log
- **AND** the rebuild does not require re-running LLM extraction

#### Scenario: Projection cache differs from log
- **WHEN** a cached projection conflicts with the replayed event log
- **THEN** the replayed event log result takes precedence

### Requirement: Hub controls writes to the event log
The system MUST route state mutation requests through the Hub/runtime before appending to the event log.

Background Agents MUST submit structured mutation candidates or structured findings; they MUST NOT directly mutate `story_state.json` or append accepted events without Hub mediation.

#### Scenario: Agent submits extracted fact
- **WHEN** the Extraction Agent identifies a candidate fact from user text
- **THEN** the Agent submits the finding to the Hub/runtime
- **AND** only the Hub/runtime may accept it as a `SystemEvent` that affects projection state

#### Scenario: Agent attempts direct projection write
- **WHEN** a background Agent attempts to directly overwrite `story_state.json`
- **THEN** the system rejects that path as invalid for state mutation