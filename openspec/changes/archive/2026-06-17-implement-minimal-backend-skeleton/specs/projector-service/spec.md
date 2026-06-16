## ADDED Requirements

### Requirement: Projector service rebuilds state from event log

The system SHALL provide a projector service that rebuilds `story_state` by replaying events from the event log.

The projector MUST process events in ascending `seq` order.

The resulting `story_state` MUST contain:
- `projection_schema_version`: Schema version string
- `log_head_seq`: Highest `seq` processed
- `head_event_id`: `event_id` of the highest `seq` event
- `source_document_revision`: Document revision if tracked
- `source_document_checksum`: Document checksum if tracked
- `story`: The story state object with characters, plot_events, facts, continuity_events, project_preferences

#### Scenario: Projector rebuilds from empty log

- **WHEN** the projector rebuilds from an empty event log
- **THEN** the resulting `story_state` has empty collections
- **AND** `log_head_seq` is 0
- **AND** `head_event_id` is null

#### Scenario: Projector rebuilds from events

- **WHEN** the projector rebuilds from an event log with 5 events
- **THEN** the resulting `story_state` reflects all 5 events
- **AND** `log_head_seq` is 5
- **AND** `head_event_id` is the `event_id` of the 5th event

### Requirement: Projector handles character events

The system MUST handle `character.created` and `character.status_updated` event types.

`character.created` MUST create a new `Character` in the projection with:
- `id`: From payload `character_id`
- `name`: From payload `name`
- `status`: From payload `initial_status`
- `status_since_event_id`: The creating event's `event_id`
- `status_note`: From payload `initial_status_note`
- `gender`: From payload `gender` if present
- `relations`: From payload `relations` if present
- `known_fact_ids`: Empty array initially
- `attributes`: Empty object initially

`character.status_updated` MUST update the existing `Character`:
- `status`: From payload `new_status`
- `status_since_event_id`: The updating event's `event_id`

#### Scenario: Character is created from event

- **WHEN** a `character.created` event is processed
- **THEN** a new `Character` appears in `story_state.characters`
- **AND** the character has the specified `id`, `name`, `status`

#### Scenario: Character status is updated from event

- **WHEN** a `character.status_updated` event is processed for an existing character
- **THEN** the character's `status` is updated
- **AND** `status_since_event_id` is set to the event's `event_id`

### Requirement: Projector handles plot event events

The system MUST handle `plot_event.created` event type.

`plot_event.created` MUST create a new `PlotEvent` in the projection with:
- `id`: From payload `plot_event_id`
- `summary`: From payload `summary`
- `story_time`: From payload `story_time`
- `participant_character_ids`: From payload `participant_character_ids`
- `asserted_fact_ids`: From payload `asserted_fact_ids` or empty array
- `source_event_id`: The creating event's `event_id`

#### Scenario: Plot event is created from event

- **WHEN** a `plot_event.created` event is processed
- **THEN** a new `PlotEvent` appears in `story_state.plot_events`
- **AND** the plot event has the specified `id`, `summary`, `story_time`

### Requirement: Projector handles fact events

The system MUST handle `fact.created` event type.

`fact.created` MUST create a new `Fact` in the projection with:
- `id`: From payload `fact_id`
- `content`: From payload `content`
- `story_time`: From payload `story_time` if present
- `about_character_ids`: From payload `about_character_ids` if present
- `source_event_id`: The creating event's `event_id`
- `source_document_id`: From payload `source_document_id`
- `source_revision`: From payload `source_revision`
- `source_span`: From payload `source_span`
- `source_text_hash`: From payload `source_text_hash`
- `source_plot_event_id`: From payload `source_plot_event_id` if present
- `extraction_confidence`: From payload `extraction_confidence`
- `lifecycle_status`: From payload `lifecycle_status` or `active`

#### Scenario: Fact is created from event

- **WHEN** a `fact.created` event is processed
- **THEN** a new `Fact` appears in `story_state.facts`
- **AND** the fact traces back to its source event

### Requirement: Projector handles continuity events

The system MUST handle `continuity_event.created`, `continuity_event.ignored`, and `continuity_event.resolved` event types.

`continuity_event.created` MUST create a new `ContinuityEvent` in the projection.

`continuity_event.ignored` MUST update the `ContinuityEvent.status` to `ignored` and set `ignored_at`.

`continuity_event.resolved` MUST update the `ContinuityEvent.status` to `resolved`.

#### Scenario: Continuity event is created

- **WHEN** a `continuity_event.created` event is processed
- **THEN** a new `ContinuityEvent` appears in `story_state.continuity_events`
- **AND** the event has status `queued` or as specified

#### Scenario: Continuity event is ignored

- **WHEN** a `continuity_event.ignored` event is processed
- **THEN** the corresponding `ContinuityEvent.status` becomes `ignored`
- **AND** `ignored_at` is set to the event timestamp

### Requirement: Projector handles project preference events

The system MUST handle `project_preference.deweighting_set` and `project_preference.assumption_confirmed` event types.

These events MUST update the `project_preferences` collection in the projection.

#### Scenario: Project preference is recorded

- **WHEN** a `project_preference.assumption_confirmed` event is processed
- **THEN** a new preference entry appears in `story_state.project_preferences`
- **AND** the preference contains the confirmed assumption

### Requirement: Projector handles batch events

The system MUST handle `batch.committed` event type.

`batch.committed` MUST mark all events with matching `batch_id` as committed.

Partial batches (events with `batch_id` but no `batch.committed`) SHOULD be flagged during projection.

#### Scenario: Batch is committed

- **WHEN** a `batch.committed` event is processed
- **THEN** all events with the same `batch_id` are considered committed

### Requirement: Projector persists projection to file

The system SHALL persist the rebuilt `story_state` to `story_state.json` in the project directory.

#### Scenario: Projection is saved after rebuild

- **WHEN** the projector completes rebuilding
- **THEN** `story_state.json` contains the current projection
- **AND** the file is valid JSON matching the schema
