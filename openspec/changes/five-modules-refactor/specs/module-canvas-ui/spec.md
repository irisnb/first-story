## ADDED Requirements

### Requirement: Module canvas view

The frontend SHALL provide a canvas view displaying all five module documents.

#### Scenario: Display modules

- **WHEN** user opens the canvas view
- **THEN** the system displays five panels/cards for each module

#### Scenario: Switch between modules

- **WHEN** user clicks on a module card
- **THEN** the system shows the full content of that module document

### Requirement: Module document editor

The frontend SHALL provide a Markdown editor for editing module documents.

#### Scenario: Edit module document

- **WHEN** user clicks edit on a module
- **THEN** the system opens the editor with current content
- **AND** acquires a lock on the document

#### Scenario: Save changes

- **WHEN** user saves changes
- **THEN** the system releases the lock and updates the document

#### Scenario: Cancel edit

- **WHEN** user cancels editing
- **THEN** the system releases the lock without saving

### Requirement: Real-time preview

The frontend MAY provide a preview pane showing rendered Markdown.

#### Scenario: Preview while editing

- **WHEN** user is editing a module document
- **THEN** the system shows a live preview of the rendered content

### Requirement: Section navigation

The frontend SHALL provide navigation between sections within a module document.

#### Scenario: Jump to section

- **WHEN** user clicks on a section in the navigation
- **THEN** the editor scrolls to that section

### Requirement: System additions indicator

The frontend SHALL indicate when system has queued additions to a locked document.

#### Scenario: Show pending additions

- **WHEN** system has queued additions for a locked document
- **THEN** the UI shows a badge or indicator with the count
