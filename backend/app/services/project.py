"""Project Service - manages project directories and files.

This service implements the project-service spec:
- Create project directories
- List projects
- Open existing projects
- Track project metadata
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

from ..models import Project, StoryState
from .contradiction import ContradictionService
from .document import DocumentService
from .event_log import EventLogService
from .evidence_card import EvidenceCardService
from .extraction import ExtractionService
from .projector import ProjectorService


class ProjectService:
    """Service for managing projects."""

    def __init__(self, projects_root: Path):
        """Initialize the project service.

        Args:
            projects_root: Root directory for all projects
        """
        self.projects_root = projects_root
        self.projects_root.mkdir(parents=True, exist_ok=True)

    def _generate_project_id(self) -> str:
        """Generate a unique project ID.

        Format: proj_<timestamp>_<random>
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = uuid.uuid4().hex[:8]
        return f"proj_{timestamp}_{random_part}"

    def create_project(self, name: str) -> Project:
        """Create a new project.

        Args:
            name: Project name

        Returns:
            The created Project
        """
        project_id = self._generate_project_id()
        project_dir = self.projects_root / project_id

        # Create directory
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        now = datetime.now()
        project = Project(
            id=project_id,
            name=name,
            created_at=now,
            updated_at=now,
            version="1.0.0",
        )

        # Initialize files
        self._init_project_files(project_dir, project)

        return project

    def _init_project_files(self, project_dir: Path, project: Project) -> None:
        """Initialize project file structure.

        Creates:
        - project.json
        - story_state.json (empty)
        - project_preferences.json (empty)
        - events/00001.jsonl (empty)
        - script/current.md (empty)
        - modules/*.md (five module documents)
        """
        # project.json
        project_file = project_dir / "project.json"
        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(project.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

        # story_state.json (empty)
        state_file = project_dir / "story_state.json"
        empty_state = StoryState()
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(empty_state.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

        # project_preferences.json (empty)
        prefs_file = project_dir / "project_preferences.json"
        with open(prefs_file, "w", encoding="utf-8") as f:
            json.dump({"derived_from_head_event_id": None, "preferences": []}, f, ensure_ascii=False, indent=2)

        # events/00001.jsonl (empty file)
        events_dir = project_dir / "events"
        events_dir.mkdir(exist_ok=True)
        (events_dir / "00001.jsonl").touch()

        # script/current.md (empty file)
        script_dir = project_dir / "script"
        script_dir.mkdir(exist_ok=True)
        (script_dir / "current.md").touch()

        # modules/*.md (five module documents)
        from .module_document import ModuleDocumentService
        module_service = ModuleDocumentService(project_dir)
        module_service.init_modules()

        # llm_config.json (empty, will use env fallback)
        from .llm_config import LLMConfigService
        llm_config_service = LLMConfigService(project_dir, project.id)
        llm_config_service.init_config_file()

    def list_projects(self) -> list[Project]:
        """List all projects.

        Returns:
            List of all projects
        """
        projects = []
        for item in self.projects_root.iterdir():
            if item.is_dir():
                project_file = item / "project.json"
                if project_file.exists():
                    try:
                        with open(project_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            projects.append(Project(**data))
                    except (json.JSONDecodeError, Exception):
                        continue

        # Sort by updated_at descending
        projects.sort(key=lambda p: p.updated_at, reverse=True)
        return projects

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: The project ID

        Returns:
            The Project if found, None otherwise
        """
        project_dir = self.projects_root / project_id
        if not project_dir.exists():
            return None

        project_file = project_dir / "project.json"
        if not project_file.exists():
            return None

        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return Project(**data)

    def get_project_dir(self, project_id: str) -> Optional[Path]:
        """Get the directory path for a project.

        Args:
            project_id: The project ID

        Returns:
            The Path if project exists, None otherwise
        """
        project_dir = self.projects_root / project_id
        if project_dir.exists():
            return project_dir
        return None

    def _update_project_timestamp(self, project_id: str) -> None:
        """Update the updated_at timestamp for a project.

        Args:
            project_id: The project ID
        """
        project_dir = self.projects_root / project_id
        project_file = project_dir / "project.json"

        if not project_file.exists():
            return

        with open(project_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["updated_at"] = datetime.now().isoformat()

        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def get_services(self, project_id: str) -> Optional[tuple[EventLogService, ProjectorService]]:
        """Get the services for a project.

        Args:
            project_id: The project ID

        Returns:
            Tuple of (EventLogService, ProjectorService) if project exists
        """
        project_dir = self.get_project_dir(project_id)
        if not project_dir:
            return None

        events_dir = project_dir / "events"
        # Fetch the single Hub-cached EventLogService for this project so all
        # writers share one in-memory _next_seq under the per-project lock.
        # Without this, each call here built a fresh instance, two of which
        # could compute the same seq and write a duplicate (Oracle MUST-FIX).
        from .hub import get_hub

        event_log = get_hub().get_event_log(events_dir)
        projector = ProjectorService(event_log, project_dir)

        return event_log, projector

    def get_document_service(self, project_id: str) -> Optional[DocumentService]:
        """Get a DocumentService for a project.

        Args:
            project_id: The project ID

        Returns:
            DocumentService if project exists, None otherwise
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, _ = services
        return DocumentService(event_log)

    def get_extraction_service(self, project_id: str) -> Optional[ExtractionService]:
        """Get an ExtractionService for a project (with configured LLM provider).

        Returns None if the project does not exist. The LLM provider is built
        from the 'utility' slot; if no key is configured the service still runs its
        deterministic stage and records the LLM stage as skipped.
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, _ = services

        from .llm_provider import get_provider_for_slot

        llm = get_provider_for_slot(project_id, "utility", self)
        return ExtractionService(event_log, llm_provider=llm)

    def get_alias_resolver_service(self, project_id: str):
        """Get an AliasResolverService for a project (identity-only LLM pass).

        Returns None if the project does not exist. Like extraction, this uses
        the 'utility' slot; with no key it simply does nothing and the
        detector falls back to exact-name grouping.
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, _ = services

        from .alias_resolver import AliasResolverService
        from .llm_provider import get_provider_for_slot

        llm = get_provider_for_slot(project_id, "utility", self)
        return AliasResolverService(event_log, llm_provider=llm)

    def get_contradiction_service(
        self, project_id: str
    ) -> Optional[ContradictionService]:
        """Get a ContradictionService for a project.

        Returns None if the project does not exist. Detection is purely
        deterministic over committed Facts and never calls an LLM.
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, _ = services
        return ContradictionService(event_log)

    def get_evidence_card_service(
        self, project_id: str
    ) -> Optional[EvidenceCardService]:
        """Get an EvidenceCardService for a project.

        Returns None if the project does not exist. Handles user ignore/accept
        decisions on continuity evidence cards (append-only).
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, _ = services
        return EvidenceCardService(event_log)

    def get_dialogue_agent(self, project_id: str):
        """Get a DialogueAgent for a project (with configured LLM provider).

        Returns None if the project does not exist. With no key the agent keeps
        the user turn and returns a graceful notice (no LLM call).
        
        Uses the 'chat' slot for dialogue (highest quality).
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, projector = services

        from .dialogue import DialogueAgent
        from .llm_provider import get_provider_for_slot

        llm = get_provider_for_slot(project_id, "chat", self)
        return DialogueAgent(event_log, projector=projector, llm_provider=llm)

    def get_context_summary_service(self, project_id: str):
        """Get a ContextSummaryService for a project (with configured LLM provider).

        Returns None if the project does not exist. Uses the 'utility' slot.
        """
        services = self.get_services(project_id)
        if not services:
            return None
        event_log, projector = services

        from .context_summary import ContextSummaryService
        from .llm_provider import get_provider_for_slot

        llm = get_provider_for_slot(project_id, "utility", self)
        return ContextSummaryService(event_log, projector, llm_provider=llm)

    def get_style_memos(self, project_id: str) -> list[dict]:
        """Return active style memos as plain dicts for prompt injection.

        Empty list if the project does not exist or has none.
        """
        services = self.get_services(project_id)
        if not services:
            return []
        _, projector = services
        state = projector.load_state()
        if state is None:
            state = projector.rebuild()
        return [
            {"text": m.text, "kind": m.kind}
            for m in state.story.style_memos
            if m.status == "active"
        ]

    def get_module_document_service(self, project_id: str) -> Optional["ModuleDocumentService"]:
        """Get a ModuleDocumentService for a project.

        Args:
            project_id: The project ID

        Returns:
            ModuleDocumentService if project exists, None otherwise
        """
        project_dir = self.get_project_dir(project_id)
        if not project_dir:
            return None

        from .module_document import ModuleDocumentService
        return ModuleDocumentService(project_dir)
