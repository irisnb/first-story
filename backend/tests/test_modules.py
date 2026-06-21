"""Tests for module document functionality."""

import pytest
from pathlib import Path

from app.models.modules import (
    MODULE_NAMES,
    MODULE_SECTIONS,
    ModuleDocument,
    ModuleSection,
    ModuleLock,
    ClassificationResult,
)
from app.services.module_parser import ModuleParser, ModuleRenderer, create_default_template
from app.services.module_document import ModuleDocumentService


def test_module_names():
    """Module names should be correct."""
    assert "world" in MODULE_NAMES
    assert "characters" in MODULE_NAMES
    assert "plot" in MODULE_NAMES
    assert "theme" in MODULE_NAMES
    assert "structure" in MODULE_NAMES
    assert len(MODULE_NAMES) == 5


def test_module_sections():
    """Module sections should be defined correctly."""
    assert "总述" in MODULE_SECTIONS["world"]
    assert "主要角色" in MODULE_SECTIONS["characters"]
    assert "主线" in MODULE_SECTIONS["plot"]


def test_module_section_model():
    """ModuleSection model should work correctly."""
    section = ModuleSection(name="主要角色", content="小红：主角")
    assert section.name == "主要角色"
    assert section.content == "小红：主角"


def test_module_document_model():
    """ModuleDocument model should work correctly."""
    doc = ModuleDocument(
        name="world",
        sections={"总述": ModuleSection(name="总述", content="测试世界")},
        revision=1,
        checksum="abc123",
    )
    assert doc.name == "world"
    assert doc.revision == 1
    assert doc.get_section_content("总述") == "测试世界"


def test_module_lock_expiration():
    """ModuleLock should detect expiration correctly."""
    from datetime import datetime, timedelta
    
    # Not expired
    lock = ModuleLock(module="world", user_id="user1", ttl_seconds=300)
    assert not lock.is_expired()
    
    # Expired
    old_lock = ModuleLock(
        module="world",
        user_id="user1",
        locked_at=datetime.utcnow() - timedelta(seconds=400),
        ttl_seconds=300,
    )
    assert old_lock.is_expired()


def test_module_lock_extend():
    """ModuleLock should extend correctly."""
    lock = ModuleLock(module="world", user_id="user1", ttl_seconds=300)
    original_time = lock.locked_at
    lock.extend(600)
    assert lock.ttl_seconds == 600


def test_classification_result():
    """ClassificationResult model should work correctly."""
    result = ClassificationResult(
        module="characters",
        section="主要角色",
        content="小红：主角，女性，26岁",
        confidence=0.92,
    )
    assert result.module == "characters"
    assert result.confidence == 0.92


class TestModuleParser:
    """Tests for ModuleParser."""

    def test_parse_empty_document(self):
        """Parser should handle empty document."""
        parser = ModuleParser()
        doc = parser.parse("world", "# 世界观\n")
        assert doc.name == "world"
        assert len(doc.sections) == 6  # All expected sections

    def test_parse_with_content(self):
        """Parser should extract section content."""
        parser = ModuleParser()
        content = """# 世界观

## 总述
这是一个测试世界。

## 魔法/技术系统
- 魔法存在
- 代价是生命
"""
        doc = parser.parse("world", content)
        assert "总述" in doc.sections
        assert "测试世界" in doc.sections["总述"].content
        assert "魔法存在" in doc.sections["魔法/技术系统"].content

    def test_checksum_generated(self):
        """Parser should generate checksum."""
        parser = ModuleParser()
        doc = parser.parse("world", "# 世界观\n")
        assert doc.checksum != ""


class TestModuleRenderer:
    """Tests for ModuleRenderer."""

    def test_render_document(self):
        """Renderer should produce valid Markdown."""
        parser = ModuleParser()
        renderer = ModuleRenderer()

        doc = parser.parse("world", "# 世界观\n")
        rendered = renderer.render(doc)

        assert "# 世界观" in rendered
        assert "## 总述" in rendered

    def test_append_to_section(self):
        """Renderer should append content to section."""
        parser = ModuleParser()
        renderer = ModuleRenderer()

        doc = parser.parse("characters", "# 角色\n")
        updated = renderer.append_to_section(doc, "主要角色", "小红：主角")

        assert "小红：主角" in updated.sections["主要角色"].content
        assert updated.revision == 1

    def test_append_multiple_items(self):
        """Renderer should append multiple items."""
        parser = ModuleParser()
        renderer = ModuleRenderer()

        doc = parser.parse("characters", "# 角色\n")
        doc = renderer.append_to_section(doc, "主要角色", "小红：主角")
        doc = renderer.append_to_section(doc, "主要角色", "小明：配角")

        content = doc.sections["主要角色"].content
        assert "小红：主角" in content
        assert "小明：配角" in content


class TestModuleDocumentService:
    """Tests for ModuleDocumentService."""

    def test_init_modules(self, tmp_path):
        """Service should initialize all module documents."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()

        for module_name in MODULE_NAMES:
            module_file = tmp_path / "modules" / f"{module_name}.md"
            assert module_file.exists()

    def test_get_module(self, tmp_path):
        """Service should get module document."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()

        doc = service.get_module("world")
        assert doc is not None
        assert doc.name == "world"

    def test_get_invalid_module(self, tmp_path):
        """Service should return None for invalid module."""
        service = ModuleDocumentService(tmp_path)
        doc = service.get_module("invalid")
        assert doc is None

    def test_save_module(self, tmp_path):
        """Service should save module document."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()

        doc = service.get_module("world")
        doc = service.renderer.append_to_section(doc, "总述", "测试内容")
        saved = service.save_module(doc)

        assert saved.revision >= doc.revision

    def test_acquire_lock(self, tmp_path):
        """Service should acquire lock."""
        service = ModuleDocumentService(tmp_path)
        success, lock = service.acquire_lock("world", "user1")
        assert success
        assert lock is not None
        assert lock.user_id == "user1"

    def test_lock_conflict(self, tmp_path):
        """Service should reject conflicting lock."""
        service = ModuleDocumentService(tmp_path)
        service.acquire_lock("world", "user1")
        success, lock = service.acquire_lock("world", "user2")
        assert not success
        assert lock.user_id == "user1"

    def test_release_lock(self, tmp_path):
        """Service should release lock."""
        service = ModuleDocumentService(tmp_path)
        service.acquire_lock("world", "user1")
        success = service.release_lock("world", "user1")
        assert success
        assert service.get_lock("world") is None

    def test_system_append_without_lock(self, tmp_path):
        """System append should work without lock."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()

        success, message = service.system_append("world", "总述", "测试内容")
        assert success
        assert "Appended" in message

    def test_system_append_with_lock(self, tmp_path):
        """System append should queue when locked."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()
        service.acquire_lock("world", "user1")

        success, message = service.system_append("world", "总述", "测试内容")
        assert success
        assert "Queued" in message

    def test_process_queue_on_release(self, tmp_path):
        """Queued additions should be processed on release."""
        service = ModuleDocumentService(tmp_path)
        service.init_modules()
        service.acquire_lock("world", "user1")
        service.system_append("world", "总述", "测试内容")

        service.release_lock("world", "user1")

        doc = service.get_module("world")
        assert "测试内容" in doc.sections["总述"].content


def test_create_default_template():
    """Default template should have correct structure."""
    template = create_default_template("world")
    assert "# 世界观" in template
    assert "## 总述" in template
    assert "## 魔法/技术系统" in template
