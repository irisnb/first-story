## ADDED Requirements

### Requirement: Append-only system event log
The system SHALL use an append-only event log as the source of truth for AI-structured story state mutations and project preferences that affect system judgment or delivery.

User-authored script documents remain the source of truth for the user's original prose. The event log records accepted structured interpretations, findings, preferences, and status changes derived from that prose.

Each accepted log entry MUST be a `SystemEvent` with at least:
- `event_id`: globally unique event identity (recommended: UUIDv7 or ULID).
- `idempotency_key`: stable deduplication key for retry-safe acceptance.
- `seq`: monotonically increasing log sequence assigned by the Hub/runtime.
- `timestamp`: wall-clock write time in ISO 8601 format.
- `type`: machine-readable mutation type in domain naming format (e.g., `character.created`, `fact.created`, `plot_event.created`, `continuity_event.created`).
- `schema_version`: schema version for event payload structure.
- `payload`: mutation-specific structured data.
- `base_state_version`: state version observed when the event was proposed.
- `actor`: origin of the event, such as user, Dialogue Gateway, Extraction Agent, or Hub.

For events produced by a multi-event operation, the entry MUST also include `batch_id` or equivalent correlation metadata.

The event log SHOULD be stored in JSONL (NDJSON) format for efficient append operations and crash recovery.

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
The system MUST use `idempotency_key`, not `event_id`, as the idempotency key for event acceptance.

A repeated event with the same `idempotency_key` MUST NOT create duplicate log entries or duplicate projection changes, even when the retry proposes a different `event_id`.

For LLM extraction output, the `idempotency_key` SHOULD be derived from at least:
- `source_document_id`
- `source_revision`
- `source_span`
- extractor version
- mutation type

#### Scenario: Duplicate event is received
- **WHEN** the Hub receives a `SystemEvent` whose `idempotency_key` already exists in the event log
- **THEN** the system does not append a second log entry
- **AND** the resulting projection remains unchanged by the duplicate submission

#### Scenario: Same retry proposes a different event id
- **WHEN** an Extraction Agent retries the same source span and proposes a new `event_id`
- **AND** the retry keeps the same `idempotency_key`
- **THEN** the Hub treats it as the same mutation attempt and does not create duplicate facts

### Requirement: Multi-event extraction batches are replay-safe
The system MUST preserve enough batch metadata to identify events produced by the same extraction pass.

If a single extraction pass produces multiple accepted `SystemEvent` entries, the Hub/runtime MUST either:
- append the whole batch atomically, or
- append member events with `batch_id` and accept a `batch.committed` marker before projection replay applies the batch.

Projection rebuild MUST NOT silently apply a partial extraction batch as if it were complete.

#### Scenario: Extraction batch is interrupted
- **WHEN** a slow extraction writes character and fact events but crashes before the batch is complete
- **THEN** projection replay can detect the incomplete `batch_id`
- **AND** the system can ignore, resume, or repair the batch without treating partial state as complete

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

#### Scenario: Source prose has not yet been extracted
- **WHEN** the script document contains user prose that has no corresponding accepted extraction events
- **THEN** replaying the event log can only recover the last accepted structured projection
- **AND** the system must treat the remaining prose as pending extraction rather than claiming full recovery from the event log

### Requirement: Project preferences that affect judgment are logged
Project preferences, confirmed assumptions, ignore rules, or deweighting rules that affect contradiction detection or delivery MUST be accepted as `SystemEvent` entries before they affect projection state.

Derived files such as `project_preferences.json` MAY exist as caches or UI-facing projections, but they MUST NOT become an independent source of truth for system judgment.

Pure UI preferences that do not affect extraction, contradiction detection, delivery priority, or reminder wording MAY stay outside the story state projection, but their boundary MUST be explicit.

#### Scenario: User confirms a project assumption
- **WHEN** the user explicitly confirms "姐姐是鬼魂" as a project assumption
- **THEN** the Hub accepts a logged setting/preference event before that assumption affects future contradiction detection

#### Scenario: User only ignores a continuity finding
- **WHEN** the user chooses to ignore a single continuity finding
- **THEN** the system records the finding status change
- **AND** does not create a confirmed project assumption from that ignore action alone

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
