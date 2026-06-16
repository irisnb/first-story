"""Tests for ProjectService."""

import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))



class TestProjectService:
    """Tests for ProjectService."""

    def test_create_project(self, project_service):
        """Test project creation."""
        project = project_service.create_project("My Story")
        assert project.id.startswith("proj_")
        assert project.name == "My Story"
        assert project.version == "1.0.0"

    def test_create_project_creates_directory(self, project_service, projects_root):
        """Test that project creation creates directory structure."""
        project = project_service.create_project("Test")
        project_dir = projects_root / project.id
        assert project_dir.exists()

        # Check required files
        assert (project_dir / "project.json").exists()
        assert (project_dir / "story_state.json").exists()
        assert (project_dir / "project_preferences.json").exists()
        assert (project_dir / "events" / "00001.jsonl").exists()
        assert (project_dir / "script" / "current.md").exists()

    def test_list_projects(self, project_service):
        """Test listing projects."""
        project_service.create_project("Story 1")
        project_service.create_project("Story 2")
        project_service.create_project("Story 3")

        projects = project_service.list_projects()
        assert len(projects) == 3

    def test_list_projects_empty(self, project_service):
        """Test listing projects when empty."""
        projects = project_service.list_projects()
        assert len(projects) == 0

    def test_get_project(self, project_service):
        """Test getting a project by ID."""
        created = project_service.create_project("My Story")
        project = project_service.get_project(created.id)
        assert project is not None
        assert project.name == "My Story"

    def test_get_project_not_found(self, project_service):
        """Test getting a non-existent project."""
        project = project_service.get_project("nonexistent")
        assert project is None

    def test_get_project_dir(self, project_service, projects_root):
        """Test getting project directory."""
        created = project_service.create_project("My Story")
        project_dir = project_service.get_project_dir(created.id)
        assert project_dir is not None
        assert project_dir == projects_root / created.id

    def test_unique_project_ids(self, project_service):
        """Test that project IDs are unique."""
        p1 = project_service.create_project("Story 1")
        p2 = project_service.create_project("Story 2")
        assert p1.id != p2.id

    def test_get_services(self, project_service):
        """Test getting services for a project."""
        project = project_service.create_project("Test")
        services = project_service.get_services(project.id)
        assert services is not None
        event_log, projector = services
        assert event_log is not None
        assert projector is not None

    def test_get_services_not_found(self, project_service):
        """Test getting services for non-existent project."""
        services = project_service.get_services("nonexistent")
        assert services is None
