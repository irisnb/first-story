"""Test fixtures for the First Story backend tests."""

import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services import ProjectService, ProjectorService


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def projects_root(temp_dir):
    """Create a projects root directory."""
    projects = temp_dir / "projects"
    projects.mkdir(parents=True, exist_ok=True)
    return projects


@pytest.fixture
def project_service(projects_root):
    """Create a ProjectService instance."""
    return ProjectService(projects_root)


@pytest.fixture
def sample_project(project_service):
    """Create a sample project for testing."""
    return project_service.create_project("Test Story")


@pytest.fixture
def event_log_service(sample_project, project_service):
    """Create an EventLogService for the sample project."""
    services = project_service.get_services(sample_project.id)
    return services[0]


@pytest.fixture
def projector_service(event_log_service, project_service, sample_project):
    """Create a ProjectorService for the sample project."""
    project_dir = project_service.get_project_dir(sample_project.id)
    return ProjectorService(event_log_service, project_dir)
