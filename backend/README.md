# First Story Backend

Backend API for First Story - a screenplay writing assistant.

## Requirements

- Python 3.11+
- pip or uv

## Installation

```bash
# Using pip
pip install -r requirements.txt

# Or using uv (recommended)
uv pip install -r requirements.txt
```

## Running

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once running, access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_event_log.py -v
```

## Project Structure

```
backend/
├── app/
│   ├── models/          # Pydantic data models
│   │   ├── common.py    # Common types (StoryTime, etc.)
│   │   ├── events.py    # SystemEvent definitions
│   │   ├── characters.py
│   │   ├── facts.py
│   │   ├── continuity.py
│   │   ├── state.py     # StoryState projection
│   │   └── api.py       # API request/response models
│   ├── services/        # Core business logic
│   │   ├── event_log.py # Event log management
│   │   ├── projector.py # State projection
│   │   └── project.py   # Project management
│   ├── api/             # FastAPI routes
│   ├── config.py        # Configuration
│   └── main.py          # Application entry point
├── tests/               # Unit tests
├── pyproject.toml
└── requirements.txt
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/projects` | List all projects |
| POST | `/api/v1/projects` | Create a new project |
| GET | `/api/v1/projects/{id}` | Get project details |
| GET | `/api/v1/projects/{id}/events` | List events |
| POST | `/api/v1/projects/{id}/events` | Append event |
| GET | `/api/v1/projects/{id}/state` | Get current state |
| POST | `/api/v1/projects/{id}/state/rebuild` | Rebuild state |

## Configuration

Environment variables (prefix `FIRST_STORY_`):

- `FIRST_STORY_PROJECTS_ROOT`: Root directory for projects (default: `projects`)
- `FIRST_STORY_DEBUG`: Enable debug mode (default: `false`)

## Architecture

The backend follows a layered architecture:

1. **Models Layer**: Pydantic models that define data structures aligned with OpenSpec specs
2. **Services Layer**: Core business logic (event log, projector, project management)
3. **API Layer**: Thin FastAPI routes that delegate to services

### Event Log

The event log is an append-only JSONL file. Each event has:
- `event_id`: Unique identifier (UUIDv7 recommended)
- `idempotency_key`: Deduplication key
- `seq`: Monotonically increasing sequence number
- `type`: Event type (e.g., `character.created`)
- `payload`: Event-specific data

### State Projection

The story state is a projection rebuilt by replaying events. It contains:
- Characters
- Plot events
- Facts
- Continuity events
- Project preferences
