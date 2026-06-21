#!/usr/bin/env python3
"""Migration script: flat lists → module MD documents.

This script migrates existing data from the old flat list structure
(facts[], characters[], plot_events[]) to the new module document structure.

Usage:
    python scripts/migrate_to_modules.py <project_dir>
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.module_parser import create_default_template
from app.models.modules import MODULE_NAMES


def migrate_project(project_dir: Path) -> dict[str, Any]:
    """Migrate a single project.

    Args:
        project_dir: Path to the project directory

    Returns:
        Migration statistics
    """
    stats = {
        "facts_migrated": 0,
        "characters_migrated": 0,
        "plot_events_migrated": 0,
        "errors": [],
    }

    # Load story state
    state_file = project_dir / "story_state.json"
    if not state_file.exists():
        stats["errors"].append("story_state.json not found")
        return stats

    with open(state_file, "r", encoding="utf-8") as f:
        state = json.load(f)

    story = state.get("story", {})

    # Create modules directory
    modules_dir = project_dir / "modules"
    modules_dir.mkdir(parents=True, exist_ok=True)

    # Initialize module contents
    module_contents: dict[str, list[str]] = {name: [] for name in MODULE_NAMES}

    # Migrate facts → world.md
    facts = story.get("facts", [])
    for fact in facts:
        if fact.get("acceptance_status") == "committed":
            content = fact.get("content", "")
            if content:
                module_contents["world"].append(f"- {content}")
                stats["facts_migrated"] += 1

    # Migrate characters → characters.md
    characters = story.get("characters", [])
    for char in characters:
        name = char.get("name", "")
        if name:
            parts = [name]
            gender = char.get("gender")
            if gender:
                parts.append(f"性别：{gender}")
            status = char.get("status", "unknown")
            parts.append(f"状态：{status}")
            module_contents["characters"].append(f"- {', '.join(parts)}")
            stats["characters_migrated"] += 1

    # Migrate plot_events → plot.md
    plot_events = story.get("plot_events", [])
    for event in plot_events:
        summary = event.get("summary", "")
        if summary:
            module_contents["plot"].append(f"- {summary}")
            stats["plot_events_migrated"] += 1

    # Write module documents
    module_titles = {
        "world": "世界观",
        "characters": "角色",
        "plot": "情节",
        "theme": "主题",
        "structure": "结构",
    }

    section_mappings = {
        "world": "细节记录",
        "characters": "主要角色",
        "plot": "关键事件",
        "theme": "核心主题",
        "structure": "幕布结构",
    }

    for module_name in MODULE_NAMES:
        module_file = modules_dir / f"{module_name}.md"

        # Start with default template
        template = create_default_template(module_name)

        # Add migrated content to appropriate section
        if module_contents[module_name]:
            section_name = section_mappings.get(module_name, "总述")
            # Insert content after the section header
            lines = template.split("\n")
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if line.strip() == f"## {section_name}":
                    for content in module_contents[module_name]:
                        new_lines.append(content)
            template = "\n".join(new_lines)

        with open(module_file, "w", encoding="utf-8") as f:
            f.write(template)

    return stats


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python migrate_to_modules.py <project_dir>")
        print("       python migrate_to_modules.py --all  # Migrate all projects")
        sys.exit(1)

    if sys.argv[1] == "--all":
        # Migrate all projects
        projects_root = Path(__file__).parent.parent / "projects"
        if not projects_root.exists():
            print(f"Projects directory not found: {projects_root}")
            sys.exit(1)

        for project_dir in projects_root.iterdir():
            if project_dir.is_dir() and (project_dir / "story_state.json").exists():
                print(f"\nMigrating {project_dir.name}...")
                stats = migrate_project(project_dir)
                print(f"  Facts: {stats['facts_migrated']}")
                print(f"  Characters: {stats['characters_migrated']}")
                print(f"  Plot events: {stats['plot_events_migrated']}")
                if stats["errors"]:
                    print(f"  Errors: {stats['errors']}")
    else:
        project_dir = Path(sys.argv[1])
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)

        stats = migrate_project(project_dir)
        print(f"Migration complete:")
        print(f"  Facts: {stats['facts_migrated']}")
        print(f"  Characters: {stats['characters_migrated']}")
        print(f"  Plot events: {stats['plot_events_migrated']}")
        if stats["errors"]:
            print(f"  Errors: {stats['errors']}")


if __name__ == "__main__":
    main()
