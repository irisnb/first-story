## ADDED Requirements

### Requirement: LLM configuration storage

The system SHALL store LLM configurations per project in a dedicated file `llm_config.json`.

Each configuration SHALL include:
- `slot`: Configuration slot name (`chat` or `utility`)
- `provider`: LLM provider name (e.g., `openai`, `anthropic`, `local`)
- `model`: Model identifier (e.g., `gpt-4`, `claude-3-opus`)
- `api_endpoint`: API endpoint URL
- `api_key`: Encrypted API key

#### Scenario: Create default config on project creation

- **WHEN** a new project is created
- **THEN** the system creates an empty `llm_config.json` file

#### Scenario: Load config from file

- **WHEN** the system needs an LLM configuration
- **THEN** it loads from `llm_config.json` if exists
- **AND** falls back to environment variables if not configured

### Requirement: API key encryption

The system SHALL encrypt API keys before storage using Fernet symmetric encryption.

The encryption key SHALL be read from environment variable `FIRST_STORY_ENCRYPTION_KEY`.

#### Scenario: Encrypt API key on save

- **WHEN** user saves an API key
- **THEN** the system encrypts it before writing to file

#### Scenario: Decrypt API key on use

- **WHEN** the system needs to use an API key
- **THEN** it decrypts the stored value

### Requirement: LLM config API endpoints

The system SHALL provide endpoints to manage LLM configurations:

- `GET /api/v1/projects/{project_id}/llm-config` — List all configs
- `GET /api/v1/projects/{project_id}/llm-config/{slot}` — Get specific config
- `PUT /api/v1/projects/{project_id}/llm-config/{slot}` — Update config

#### Scenario: List all configs

- **WHEN** client requests `GET /llm-config`
- **THEN** the system returns all configured slots with masked API keys

#### Scenario: Get specific config

- **WHEN** client requests `GET /llm-config/chat`
- **THEN** the system returns the chat config with masked API key

#### Scenario: Update config

- **WHEN** client sends `PUT /llm-config/chat` with new config
- **THEN** the system validates, encrypts API key, and saves

### Requirement: API key masking

The system SHALL mask API keys in API responses, showing only the last 4 characters.

#### Scenario: Masked key in response

- **WHEN** API key is `sk-abcdefghijklmnop`
- **THEN** response shows `****mnop`

### Requirement: Dual configuration slots

The system SHALL support two fixed configuration slots:

- `chat`: Main dialogue window LLM
- `utility`: Background tasks (classification, summarization)

#### Scenario: Get chat LLM

- **WHEN** DialogueAgent needs an LLM
- **THEN** it uses the `chat` slot configuration

#### Scenario: Get utility LLM

- **WHEN** ClassifyService or ContextSummaryService needs an LLM
- **THEN** it uses the `utility` slot configuration

### Requirement: Configuration fallback

The system SHALL fall back to environment variables when project config is empty.

#### Scenario: No project config, use env var

- **WHEN** project has no LLM config for a slot
- **AND** environment variable `FIRST_STORY_LLM_API_KEY` is set
- **THEN** the system uses the environment variable

#### Scenario: No config at all

- **WHEN** neither project config nor environment variable is set
- **THEN** the system returns a graceful error message
