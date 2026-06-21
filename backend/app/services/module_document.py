"""Module Document Service - manages module MD files.

This service implements the module-documents spec:
- Create module documents on project creation
- Read/write module MD files
- Manage document locks
- Queue system additions during locks
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
import asyncio
from collections import defaultdict

from app.models.modules import MODULE_NAMES, ModuleDocument, ModuleLock
from app.services.module_parser import ModuleParser, ModuleRenderer, create_default_template


class QueuedAddition:
    """A queued addition waiting for lock release."""

    def __init__(
        self,
        section_name: str,
        content: str,
        added_at: datetime = None,
    ):
        self.section_name = section_name
        self.content = content
        self.added_at = added_at or datetime.utcnow()


class ModuleDocumentService:
    """Service for managing module documents."""

    def __init__(self, project_dir: Path):
        """Initialize the module document service.

        Args:
            project_dir: Path to the project directory
        """
        self.project_dir = project_dir
        self.modules_dir = project_dir / "modules"
        self.parser = ModuleParser()
        self.renderer = ModuleRenderer()
        self._locks: dict[str, ModuleLock] = {}  # In-memory lock storage
        self._queues: dict[str, list[QueuedAddition]] = defaultdict(list)  # Queued additions per module

    def init_modules(self) -> None:
        """Initialize all five module documents with default templates.

        Creates the modules/ directory and five .md files.
        """
        self.modules_dir.mkdir(parents=True, exist_ok=True)

        for module_name in MODULE_NAMES:
            module_file = self.modules_dir / f"{module_name}.md"
            if not module_file.exists():
                template = create_default_template(module_name)
                with open(module_file, "w", encoding="utf-8") as f:
                    f.write(template)

    def get_module(self, module_name: str) -> Optional[ModuleDocument]:
        """Get a module document by name.

        Args:
            module_name: Name of the module (world, characters, etc.)

        Returns:
            ModuleDocument if found, None otherwise
        """
        if module_name not in MODULE_NAMES:
            return None

        module_file = self.modules_dir / f"{module_name}.md"
        if not module_file.exists():
            return None

        with open(module_file, "r", encoding="utf-8") as f:
            content = f.read()

        return self.parser.parse(module_name, content)

    def save_module(self, doc: ModuleDocument) -> ModuleDocument:
        """Save a module document.

        Args:
            doc: ModuleDocument to save

        Returns:
            Updated ModuleDocument with new revision and checksum
        """
        if doc.name not in MODULE_NAMES:
            raise ValueError(f"Invalid module name: {doc.name}")

        # Render to Markdown
        content = self.renderer.render(doc)

        # Save to file
        self.modules_dir.mkdir(parents=True, exist_ok=True)
        module_file = self.modules_dir / f"{doc.name}.md"
        with open(module_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Re-parse to get updated checksum
        return self.parser.parse(doc.name, content)

    def append_to_section(
        self,
        module_name: str,
        section_name: str,
        content: str,
    ) -> Optional[ModuleDocument]:
        """Append content to a section of a module document.

        Args:
            module_name: Name of the module
            section_name: Name of the section
            content: Content to append (will be formatted as list item)

        Returns:
            Updated ModuleDocument if successful, None otherwise
        """
        doc = self.get_module(module_name)
        if not doc:
            return None

        updated_doc = self.renderer.append_to_section(doc, section_name, content)
        return self.save_module(updated_doc)

    # Lock management

    def acquire_lock(
        self,
        module_name: str,
        user_id: str,
        ttl_seconds: int = 300,
    ) -> tuple[bool, Optional[ModuleLock]]:
        """Try to acquire a lock on a module document.

        Args:
            module_name: Name of the module to lock
            user_id: ID of the user acquiring the lock
            ttl_seconds: Lock TTL in seconds (default 5 min)

        Returns:
            Tuple of (success, lock_or_existing_lock)
        """
        if module_name not in MODULE_NAMES:
            return False, None

        existing_lock = self._locks.get(module_name)

        # Check if lock exists and is not expired
        if existing_lock and not existing_lock.is_expired():
            if existing_lock.user_id == user_id:
                # Same user, extend lock
                existing_lock.extend(ttl_seconds)
                return True, existing_lock
            # Different user, lock conflict
            return False, existing_lock

        # No lock or expired, acquire new lock
        new_lock = ModuleLock(
            module=module_name,
            user_id=user_id,
            ttl_seconds=ttl_seconds,
        )
        self._locks[module_name] = new_lock
        return True, new_lock

    def release_lock(self, module_name: str, user_id: str) -> bool:
        """Release a lock on a module document and process queued additions.

        Args:
            module_name: Name of the module to unlock
            user_id: ID of the user releasing the lock

        Returns:
            True if lock was released, False otherwise
        """
        existing_lock = self._locks.get(module_name)

        if not existing_lock:
            return True  # No lock to release

        if existing_lock.user_id != user_id:
            return False  # Wrong user

        del self._locks[module_name]

        # Process queued additions after releasing lock
        self.process_queued_additions(module_name)

        return True

    def get_lock(self, module_name: str) -> Optional[ModuleLock]:
        """Get the current lock on a module document.

        Args:
            module_name: Name of the module

        Returns:
            ModuleLock if exists and not expired, None otherwise
        """
        lock = self._locks.get(module_name)
        if lock and not lock.is_expired():
            return lock
        return None

    def extend_lock(self, module_name: str, user_id: str) -> bool:
        """Extend an existing lock.

        Args:
            module_name: Name of the module
            user_id: ID of the user holding the lock

        Returns:
            True if lock was extended, False otherwise
        """
        lock = self._locks.get(module_name)
        if not lock or lock.user_id != user_id:
            return False

        if lock.is_expired():
            return False

        lock.extend()
        return True

    # Queue management for system additions

    def queue_addition(self, module_name: str, section_name: str, content: str) -> None:
        """Queue an addition for when lock is released.

        Args:
            module_name: Name of the module
            section_name: Name of the section
            content: Content to append
        """
        if module_name not in MODULE_NAMES:
            return

        addition = QueuedAddition(section_name=section_name, content=content)
        self._queues[module_name].append(addition)

    def get_queued_additions(self, module_name: str) -> list[QueuedAddition]:
        """Get queued additions for a module.

        Args:
            module_name: Name of the module

        Returns:
            List of queued additions
        """
        return self._queues.get(module_name, [])

    def process_queued_additions(self, module_name: str) -> int:
        """Process all queued additions for a module.

        Called when lock is released.

        Args:
            module_name: Name of the module

        Returns:
            Number of additions processed
        """
        queue = self._queues.get(module_name, [])
        if not queue:
            return 0

        count = 0
        for addition in queue:
            result = self.append_to_section(module_name, addition.section_name, addition.content)
            if result:
                count += 1

        # Clear queue after processing
        self._queues[module_name] = []
        return count

    def system_append(
        self,
        module_name: str,
        section_name: str,
        content: str,
    ) -> tuple[bool, str]:
        """System append - respects lock, queues if locked.

        Args:
            module_name: Name of the module
            section_name: Name of the section
            content: Content to append

        Returns:
            Tuple of (success, message)
        """
        if module_name not in MODULE_NAMES:
            return False, f"Invalid module: {module_name}"

        # Check for lock
        lock = self.get_lock(module_name)
        if lock:
            # Queue the addition
            self.queue_addition(module_name, section_name, content)
            return True, f"Queued (module locked by {lock.user_id})"

        # No lock, append directly
        result = self.append_to_section(module_name, section_name, content)
        if result:
            return True, "Appended successfully"
        return False, "Failed to append"
