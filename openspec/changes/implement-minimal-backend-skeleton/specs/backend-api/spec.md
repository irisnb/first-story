## ADDED Requirements

### Requirement: REST API provides event and state endpoints

The system SHALL provide a REST API for event management and state queries.

The API MUST include the following endpoints:
- `GET /projects`: List all projects
- `POST /projects`: Create a new project
- `GET /projects/{project_id}`: Get project details
- `GET /projects/{project_id}/events`: List events for a project
- `POST /projects/{project_id}/events`: Append a new event
- `GET /projects/{project_id}/state`: Get current story state projection
- `POST /projects/{project_id}/state/rebuild`: Force rebuild projection from event log

All endpoints MUST return JSON responses with appropriate HTTP status codes.

#### Scenario: List projects returns empty list initially

- **WHEN** a GET request is made to `/projects` with no existing projects
- **THEN** the response has status 200
- **AND** the response body contains an empty array

#### Scenario: Create project returns new project details

- **WHEN** a POST request is made to `/projects` with a project name
- **THEN** the response has status 201
- **AND** the response body contains the new project with an `id` field

### Requirement: API validates request bodies using Pydantic models

The system MUST validate all request bodies against Pydantic models before processing.

Invalid requests MUST return HTTP 422 with detailed validation error messages.

#### Scenario: Invalid event payload is rejected

- **WHEN** a POST request is made to `/projects/{project_id}/events` with an invalid event payload
- **THEN** the response has status 422
- **AND** the response body contains validation error details

### Requirement: API generates OpenAPI documentation automatically

The system SHALL expose OpenAPI documentation at `/docs` (Swagger UI) and `/openapi.json`.

The documentation MUST accurately reflect all endpoints, request/response schemas, and error responses.

#### Scenario: OpenAPI documentation is accessible

- **WHEN** a GET request is made to `/docs`
- **THEN** the response has status 200
- **AND** the response contains Swagger UI documentation

### Requirement: API handles errors gracefully

The system MUST return consistent error response format for all errors.

Error responses MUST include at least:
- `detail`: Human-readable error message
- `status`: HTTP status code

#### Scenario: Project not found returns 404

- **WHEN** a GET request is made to `/projects/nonexistent-id`
- **THEN** the response has status 404
- **AND** the response body contains a `detail` field explaining the error
