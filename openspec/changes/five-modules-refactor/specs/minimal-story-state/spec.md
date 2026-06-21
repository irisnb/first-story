## ADDED Requirements

### Requirement: Module documents as source of truth

The system SHALL derive story state from module Markdown documents in addition to the event log.

The story state projection MUST include:
- `modules`: a collection of parsed module document content.

Each module in `modules` MUST include:
- `name`: module name (world, characters, plot, theme, structure).
- `sections`: dictionary mapping section names to their content.
- `revision`: document revision number.
- `checksum`: content hash for optimistic locking.

#### Scenario: Module content available in projection

- **WHEN** the system rebuilds the projection
- **THEN** the story state contains parsed content from all five module documents

### Requirement: Module document syncs to event log

The system SHALL generate events when module documents are modified.

When a user edits a module document:
- The system MUST generate a `module_document.updated` event.
- The event MUST include the module name, changed sections, and revision.

#### Scenario: Edit generates event

- **WHEN** user saves changes to world.md
- **THEN** the system creates a `module_document.updated` event with module="world"

## MODIFIED Requirements

### Requirement: Story state projection contains MVP objects

The system SHALL define a minimal `story_state` projection for the MVP continuity loop.

The projection MUST contain at least these object collections:
- `characters`: `Character` objects.
- `plot_events`: `PlotEvent` objects.
- `facts`: `Fact` objects.
- `continuity_events`: `ContinuityEvent` objects.
- `project_preferences`: project-level preferences, deweighting rules, and explicitly confirmed assumptions that affect system judgment.
- `modules`: parsed module document content (NEW).

Theme and structure modules MAY remain empty shells for this MVP state foundation.

The projection MAY also include:
- `story_clock`: structured story timeline state (current time, reference point, confidence).

#### Scenario: MVP projection is available
- **WHEN** the system rebuilds the current projection from the event log
- **THEN** the resulting story state contains collections for characters, plot events, facts, continuity events, project preferences, and modules

#### Scenario: Module documents are parsed into projection
- **WHEN** the system rebuilds the projection
- **THEN** the modules collection contains parsed content from all five module documents
- **AND** each module has its sections dictionary populated
