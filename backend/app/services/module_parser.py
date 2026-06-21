"""Module document parser and renderer services.

This implements the MD parser/renderer for five story modules.
"""

import hashlib
import re
from typing import Optional

from markdown_it import MarkdownIt

from app.models.modules import (
    MODULE_SECTIONS,
    ModuleDocument,
    ModuleSection,
)


class ModuleParser:
    """Parse Markdown documents into structured ModuleDocument objects."""

    def __init__(self) -> None:
        self.md = MarkdownIt()

    def parse(self, module_name: str, content: str) -> ModuleDocument:
        """Parse a Markdown document into a ModuleDocument.

        Args:
            module_name: Name of the module (world, characters, etc.)
            content: Raw Markdown content

        Returns:
            ModuleDocument with parsed sections
        """
        # Get expected sections for this module
        expected_sections = MODULE_SECTIONS.get(module_name, [])

        # Parse sections by ## headers
        sections: dict[str, ModuleSection] = {}

        # Initialize all expected sections with empty content
        for section_name in expected_sections:
            sections[section_name] = ModuleSection(name=section_name, content="")

        # Split content by ## headers
        current_section: Optional[str] = None
        current_content: list[str] = []

        for line in content.split("\n"):
            # Check for ## header
            header_match = re.match(r"^##\s+(.+)$", line)
            if header_match:
                # Save previous section content
                if current_section and current_section in sections:
                    sections[current_section].content = "\n".join(current_content).strip()
                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Save last section content
        if current_section and current_section in sections:
            sections[current_section].content = "\n".join(current_content).strip()

        # Calculate checksum
        checksum = hashlib.sha256(content.encode()).hexdigest()[:16]

        return ModuleDocument(
            name=module_name,
            sections=sections,
            revision=0,
            checksum=checksum,
            raw_content=content,
        )


class ModuleRenderer:
    """Render ModuleDocument objects back to Markdown."""

    def render(self, doc: ModuleDocument) -> str:
        """Render a ModuleDocument to Markdown.

        Args:
            doc: ModuleDocument to render

        Returns:
            Markdown string
        """
        # Get expected section order for this module
        expected_sections = MODULE_SECTIONS.get(doc.name, [])

        lines: list[str] = []

        # Add title
        module_titles = {
            "world": "世界观",
            "characters": "角色",
            "plot": "情节",
            "theme": "主题",
            "structure": "结构",
        }
        lines.append(f"# {module_titles.get(doc.name, doc.name)}")
        lines.append("")

        # Add each section in order
        for section_name in expected_sections:
            lines.append(f"## {section_name}")
            section = doc.sections.get(section_name)
            if section and section.content:
                lines.append(section.content)
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def append_to_section(
        self,
        doc: ModuleDocument,
        section_name: str,
        content: str,
    ) -> ModuleDocument:
        """Append a list item to a section.

        Args:
            doc: ModuleDocument to modify
            section_name: Section to append to
            content: Content to append (will be formatted as list item)

        Returns:
            New ModuleDocument with updated content
        """
        import copy

        new_doc = copy.deepcopy(doc)

        # Get the section
        section = new_doc.sections.get(section_name)
        if not section:
            # Create section if it doesn't exist
            section = ModuleSection(name=section_name, content="")
            new_doc.sections[section_name] = section

        # Append as list item
        current = section.content.strip()
        new_item = f"- {content}"

        if current:
            section.content = f"{current}\n{new_item}"
        else:
            section.content = new_item

        # Update revision and checksum
        new_doc.revision += 1
        new_doc.raw_content = self.render(new_doc)
        new_doc.checksum = hashlib.sha256(new_doc.raw_content.encode()).hexdigest()[:16]

        return new_doc


def create_default_template(module_name: str) -> str:
    """Create a default template for a module.

    Args:
        module_name: Name of the module

    Returns:
        Markdown template string
    """
    expected_sections = MODULE_SECTIONS.get(module_name, [])

    module_titles = {
        "world": "世界观",
        "characters": "角色",
        "plot": "情节",
        "theme": "主题",
        "structure": "结构",
    }

    lines = [f"# {module_titles.get(module_name, module_name)}", ""]

    for section_name in expected_sections:
        lines.append(f"## {section_name}")
        lines.append("")

    return "\n".join(lines).strip() + "\n"
