## ADDED Requirements

### Requirement: Story state projection contains MVP objects
The system SHALL define a minimal `story_state` projection for the MVP continuity loop.

The projection MUST contain at least these object collections:
- `characters`: `Character` objects.
- `plot_events`: `PlotEvent` objects.
- `facts`: `Fact` objects.
- `continuity_events`: `ContinuityEvent` objects.
- `user_preferences`: `UserPreference` records or equivalent preference projection.

Theme and structure modules MAY remain empty shells for this MVP state foundation.

#### Scenario: MVP projection is available
- **WHEN** the system rebuilds the current projection from the event log
- **THEN** the resulting story state contains collections for characters, plot events, facts, continuity events, and user preferences

### Requirement: Character projection is machine-readable without losing human notes
A `Character` object MUST include at least:
- `id`: stable identifier.
- `name`: display name.
- `status`: machine-readable current status.
- `status_since_event_id`: `SystemEvent.event_id` from which the current status became effective.
- `status_note`: optional human-readable note that is not used for deterministic contradiction checks.
- `known_fact_ids`: facts known to this character, when tracked.
- `relations`: relationship records to other characters.

Deterministic contradiction checks MUST use `status` and MUST NOT parse `status_note` as authoritative machine state.

#### Scenario: Character death is represented structurally
- **WHEN** the story asserts that a character is dead
- **THEN** the character projection can represent that state in `status`
- **AND** can trace the status to `status_since_event_id`

#### Scenario: Status note does not override machine status
- **WHEN** `status` is `alive` and `status_note` contains ambiguous prose
- **THEN** deterministic contradiction checks use `status`
- **AND** do not infer a different machine status from `status_note`

### Requirement: PlotEvent projection stores story events separately from SystemEvent
A `PlotEvent` object MUST represent an event inside the story world, not an event log entry.

A `PlotEvent` MUST include at least:
- `id`: stable identifier.
- `summary`: human-readable summary.
- `story_time`: structured story time value.
- `participant_character_ids`: involved characters.
- `asserted_fact_ids`: facts asserted by this plot event.
- `source_event_id`: `SystemEvent.event_id` that introduced or updated this plot event.

#### Scenario: Story event is not confused with log entry
- **WHEN** the user writes that a character called someone yesterday
- **THEN** the projection can contain a `PlotEvent` for the story-world call
- **AND** that `PlotEvent` remains distinct from the `SystemEvent` that recorded the extraction/update

### Requirement: StoryTime supports absolute, relative, and unknown time
The `story_time` value for a `PlotEvent` MUST support at least three forms:
- `absolute`: comparable concrete time value when known.
- `relative`: relation to an anchor with direction and optional distance.
- `unknown`: explicit unknown or unavailable time.

`story_time` MUST include confidence or equivalent uncertainty metadata.

The data model MUST support this structure even when natural language parsing is performed by a later Extraction Agent capability.

#### Scenario: Relative time is represented
- **WHEN** source text says an event occurred “ten years before” another story event
- **THEN** `story_time` can represent a relative anchor, direction, and distance
- **AND** can preserve confidence for that interpretation

#### Scenario: Unknown time is represented without dropping event
- **WHEN** the system cannot determine when a plot event occurred
- **THEN** the projection stores `story_time` as `unknown`
- **AND** retains the plot event and its asserted facts

### Requirement: Fact projection is the semantic evidence unit
A `Fact` object MUST represent a minimal story assertion that can be cited as evidence.

A `Fact` MUST include at least:
- `id`: stable identifier.
- `content`: human-readable assertion text or structured assertion summary.
- `source_event_id`: `SystemEvent.event_id` that introduced the fact.
- `source_plot_event_id`: optional `PlotEvent.id` when the fact comes from a story-world event.
- `about_character_ids`: related characters.
- `confidence`: extraction or assertion confidence when applicable.

#### Scenario: Fact traces back to system log
- **WHEN** a fact appears in the current projection
- **THEN** the system can trace it to the `SystemEvent` that introduced it

#### Scenario: Fact can be used as reminder evidence
- **WHEN** a continuity reminder needs evidence
- **THEN** it can cite `Fact.id` values instead of raw edit history

### Requirement: ContinuityEvent projection cites facts and preserves user choice
A `ContinuityEvent` object MUST represent a system-discovered continuity finding, not a final creative judgment.

A `ContinuityEvent` MUST include at least:
- `id`: stable identifier.
- `type`: machine-readable finding type.
- `severity`: P1-P5 delivery priority/severity.
- `confidence`: finding confidence.
- `evidence_fact_ids`: cited `Fact.id` values.
- `affected_modules`: impacted modules such as character or plot.
- `status`: lifecycle status such as new, queued, shown, ignored, resolved, or expired.
- `source_event_id`: `SystemEvent.event_id` that recorded the finding.

The system MUST cite facts as evidence and MUST NOT present a continuity finding as the single correct interpretation of the story.

#### Scenario: Dead character calls contradiction is represented
- **WHEN** one fact asserts that a character is dead and another fact asserts that the same character made a later phone call
- **THEN** the system can create a `ContinuityEvent` with both facts in `evidence_fact_ids`
- **AND** the event status can remain `new` or `queued` until delivery policy decides whether to show it

#### Scenario: User ignores continuity finding
- **WHEN** the user chooses to ignore a continuity finding
- **THEN** the `ContinuityEvent.status` can become `ignored`
- **AND** the evidence facts remain available in the projection

### Requirement: UserPreference records deweighting without deleting evidence
A `UserPreference` projection MUST support ignore rules and deweighting records for continuity findings.

A user preference MUST NOT delete original facts, original continuity events, or original event log entries.

A user preference MUST include enough information to explain what category was ignored or deweighted and when the preference was recorded.

#### Scenario: Ignored reminder lowers future priority
- **WHEN** the user repeatedly ignores a category of continuity findings
- **THEN** the system can record a preference that deweights similar future findings
- **AND** keeps the original facts and findings traceable

#### Scenario: User asks later about ignored issue
- **WHEN** the user later asks about a previously ignored issue
- **THEN** the system can still retrieve the original facts, continuity finding, and preference record