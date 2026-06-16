## ADDED Requirements

### Requirement: Project service creates project directories

The system SHALL provide a project service that creates and manages project directories.

A project directory MUST contain:
- `project.json`: Project metadata
- `story_state.json`: Current story state projection (initially empty)
- `project_preferences.json`: Project preferences projection (initially empty)
- `events/`: Directory for event log files
- `events/00001.jsonl`: Event log file (initially empty)
- `script/`: Directory for user script documents
- `script/current.md`: Current script document (initially empty)

#### Scenario: Project is created with valid name

- **WHEN** a new project is created with name "My Story"
- **THEN** a directory is created with a unique ID
- **AND** the directory contains all required files
- **AND** `project.json` contains the project name and ID

#### Scenario: Project creation fails if name is missing

- **WHEN** a project is created without a name
- **THEN** the operation fails with a validation error

### Requirement: Project service generates unique project IDs

The system MUST generate unique project IDs for each new project.

Project IDs SHOULD use the format `proj_<timestamp>_<random>` or similar unique format.

#### Scenario: Project ID is unique

- **WHEN** multiple projects are created
- **THEN** each project has a different ID

### Requirement: Project service lists projects

The system SHALL provide the ability to list all projects.

The list MUST include for each project:
- `id`: Project ID
- `name`: Project name
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

#### Scenario: List projects returns all projects

- **WHEN** projects are listed
- **THEN** all existing projects are returned
- **AND** each project includes id, name, created_at, updated_at

### Requirement: Project service opens existing projects

The system SHALL provide the ability to open an existing project by ID.

Opening a project MUST:
- Verify the project directory exists
- Load `project.json`
- Load or rebuild `story_state.json` if needed

#### Scenario: Open existing project succeeds

- **WHEN** an existing project is opened by ID
- **THEN** the project metadata is returned
- **AND** the project's story state is accessible

#### Scenario: Open non-existent project fails

- **WHEN** a non-existent project ID is requested
- **THEN** the operation fails with a not found error

### Requirement: Project service stores projects in configurable root directory

The system MUST store all project directories under a configurable root directory.

The default root directory SHOULD be `projects/` relative to the application root.

#### Scenario: Projects are stored in root directory

- **WHEN** a project is created
- **THEN** the project directory is created under the configured root directory

### Requirement: Project service tracks project metadata

The system MUST track and persist project metadata in `project.json`.

Metadata MUST include:
- `id`: Unique project identifier
- `name`: Project display name
- `created_at`: ISO 8601 creation timestamp
- `updated_at`: ISO 8601 last update timestamp
- `version`: Schema version for project metadata

#### Scenario: Project metadata is persisted

- **WHEN** a project is created
- **THEN** `project.json` is written with correct metadata
- **AND** `created_at` and `updated_at` are set to the current time

### Requirement: Project service updates project timestamp

The system MUST update `updated_at` when project state changes.

State changes include:
- Events appended to the event log
- Story state projection updated

#### Scenario: Timestamp is updated on event append

- **WHEN** an event is appended to a project
- **THEN** `updated_at` in `project.json` is updated to the current time
