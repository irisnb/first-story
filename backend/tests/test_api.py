"""Tests for API endpoints."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health endpoint."""

    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestProjectsEndpoint:
    """Tests for projects endpoints."""

    def test_list_projects_empty(self, client):
        """Test listing projects when empty."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert "total" in data

    def test_create_project(self, client):
        """Test creating a project."""
        response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Story"
        assert "id" in data

    def test_create_project_missing_name(self, client):
        """Test creating a project without name."""
        response = client.post(
            "/api/v1/projects",
            json={},
        )
        assert response.status_code == 422

    def test_get_project(self, client):
        """Test getting a project."""
        # Create first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        # Get
        response = client.get(f"/api/v1/projects/{project_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id

    def test_get_project_not_found(self, client):
        """Test getting a non-existent project."""
        response = client.get("/api/v1/projects/nonexistent")
        assert response.status_code == 404


class TestEventsEndpoint:
    """Tests for events endpoints."""

    def test_list_events_empty(self, client):
        """Test listing events when empty."""
        # Create project first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_append_event(self, client):
        """Test appending an event."""
        # Create project first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/projects/{project_id}/events",
            json={
                "event_id": "evt_001",
                "idempotency_key": "test_key_1",
                "type": "character.created",
                "payload": {"character_id": "char_001", "name": "Alice"},
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["seq"] == 1
        assert data["type"] == "character.created"

    def test_append_duplicate_event(self, client):
        """Test appending a duplicate event."""
        # Create project first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        # First event
        client.post(
            f"/api/v1/projects/{project_id}/events",
            json={
                "event_id": "evt_001",
                "idempotency_key": "duplicate_key",
                "type": "character.created",
                "payload": {"character_id": "char_001"},
            },
        )

        # Duplicate
        response = client.post(
            f"/api/v1/projects/{project_id}/events",
            json={
                "event_id": "evt_002",
                "idempotency_key": "duplicate_key",
                "type": "character.created",
                "payload": {"character_id": "char_001"},
            },
        )
        # Should still return 201 but with seq=1
        assert response.status_code == 201
        assert response.json()["seq"] == 1


class TestStateEndpoint:
    """Tests for state endpoints."""

    def test_get_state(self, client):
        """Test getting state."""
        # Create project first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        response = client.get(f"/api/v1/projects/{project_id}/state")
        assert response.status_code == 200
        data = response.json()
        assert "log_head_seq" in data
        assert "story" in data

    def test_rebuild_state(self, client):
        """Test rebuilding state."""
        # Create project first
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Test Story"},
        )
        project_id = create_response.json()["id"]

        # Add an event
        client.post(
            f"/api/v1/projects/{project_id}/events",
            json={
                "event_id": "evt_001",
                "idempotency_key": "test_key",
                "type": "character.created",
                "payload": {"character_id": "char_001", "name": "Alice"},
            },
        )

        # Rebuild
        response = client.post(f"/api/v1/projects/{project_id}/state/rebuild")
        assert response.status_code == 200
        data = response.json()
        assert "log_head_seq" in data
        assert "events_processed" in data
