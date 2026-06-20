## ADDED Requirements

### Requirement: Chat history is persisted across sessions
The system SHALL persist chat messages to the backend event log and reload them when the user returns to a project.

#### Scenario: User refreshes page and sees previous chat history
- **WHEN** user has chat history in a project
- **AND** user refreshes the browser page
- **THEN** the chat history SHALL be loaded from the backend
- **AND** all previous messages SHALL be displayed in chronological order

#### Scenario: User switches projects and sees correct chat history
- **WHEN** user switches from project A to project B
- **THEN** the chat history for project B SHALL be loaded
- **AND** messages from project A SHALL NOT appear

### Requirement: Backend provides chat history API
The backend SHALL provide an API endpoint to retrieve chat messages for a project.

#### Scenario: API returns chat messages in chronological order
- **WHEN** client requests `GET /projects/{project_id}/chat/messages`
- **THEN** the response SHALL contain all `chat.message` events for that project
- **AND** messages SHALL be sorted by timestamp in ascending order

#### Scenario: API returns empty array for project with no chat history
- **WHEN** client requests chat messages for a project with no chat history
- **THEN** the response SHALL return `{ "messages": [], "total": 0 }`

### Requirement: Frontend initializes runtime with chat history
The frontend SHALL load chat history when initializing the chat runtime for a project.

#### Scenario: Runtime is initialized with historical messages
- **WHEN** ChatRuntimeInner component mounts for a project
- **THEN** it SHALL fetch chat history from the backend
- **AND** pass the messages to `useLocalRuntime` as `initialMessages`

#### Scenario: Loading state is shown while fetching history
- **WHEN** chat history is being fetched
- **THEN** a loading indicator SHALL be displayed
- **AND** the chat interface SHALL NOT be interactive until loading completes

### Requirement: Chat history format is correctly transformed
The frontend SHALL transform backend chat message format to the runtime's expected format.

#### Scenario: Backend message is transformed to ThreadMessageLike
- **WHEN** a chat message from backend has format `{ role, content, message_id, timestamp }`
- **THEN** it SHALL be transformed to `{ role, content: [{ type: "text", text: content }], id: message_id, createdAt: timestamp }`

### Requirement: Loading failure does not block chatting
The system SHALL allow users to continue chatting even if history loading fails.

#### Scenario: Network error during history load
- **WHEN** fetching chat history fails due to network error
- **THEN** an error message SHALL be displayed
- **AND** the chat interface SHALL still be usable with empty history
- **AND** new messages SHALL be sent successfully
