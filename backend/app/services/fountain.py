"""Minimal Fountain structural parser with native source offsets.

Why hand-written instead of a ready-made library:
- The only mature pip Fountain parser (``jouvence``) cannot recognize Chinese
  character cues (standard Fountain detects cues by ALL-CAPS lines; Chinese has
  no case), it has a broken ``parse()``, and it discards source offsets.
- This change requires "source span 可定位": every extracted Fact must map back
  to an exact character range in the manuscript.

So we parse a deliberate core subset of Fountain and track byte/char offsets:
- Scene heading: line starting with INT./EXT./INT/EXT/EST/I/E or a ``.`` forced
  heading (``.`` not followed by another ``.``).
- Character cue: an ALL-CAPS-style cue line (Latin) OR a forced cue with a
  leading ``@`` (``@小明``) - the only reliable way to mark non-Latin names.
- Parenthetical: a line wholly wrapped in ``(...)`` / ``（...）`` right under a cue.
- Dialogue: non-blank lines following a cue (until a blank line).
- Action: anything else.

Characters are determined ONLY by cue structure - never guessed from prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ElementType(str, Enum):
    SCENE_HEADING = "scene_heading"
    CHARACTER = "character"
    PARENTHETICAL = "parenthetical"
    DIALOGUE = "dialogue"
    ACTION = "action"


@dataclass
class FountainElement:
    """A parsed structural element with its source span."""

    type: ElementType
    text: str
    start: int
    end: int
    # For dialogue/parenthetical: the character this line is attributed to.
    character: str | None = None


@dataclass
class FountainParseResult:
    """Result of parsing a manuscript."""

    elements: list[FountainElement] = field(default_factory=list)
    # Deterministic character set, in first-appearance order.
    characters: list[str] = field(default_factory=list)

    def dialogue_by_character(self) -> dict[str, list[FountainElement]]:
        out: dict[str, list[FountainElement]] = {}
        for el in self.elements:
            if el.type is ElementType.DIALOGUE and el.character:
                out.setdefault(el.character, []).append(el)
        return out


# Scene headings (Latin Fountain convention) + forced ``.heading``.
_SCENE_PREFIX = re.compile(
    r"^(INT\.?|EXT\.?|EST\.?|INT\.?/EXT\.?|I/E)\b",
    re.IGNORECASE,
)
# A cue line considered ALL-CAPS when it has cased letters and no lowercase.
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_UPPER = re.compile(r"[A-Z]")
_PAREN_LINE = re.compile(r"^[（(].*[）)]$")


def _is_scene_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if _SCENE_PREFIX.match(s):
        return True
    # Forced scene heading: a single leading dot (not '..').
    if s.startswith(".") and not s.startswith(".."):
        return True
    return False


def _cue_name(line: str) -> str | None:
    """Return the character name if this line is a character cue, else None.

    A cue is either:
    - forced with a leading ``@`` (``@小明`` -> ``小明``), which is the reliable
      way to mark non-Latin names; or
    - an ALL-CAPS Latin line (has uppercase, no lowercase), optionally with a
      ``(V.O.)``-style extension.
    """
    s = line.strip()
    if not s:
        return None
    if s.startswith("@"):
        name = s[1:].strip()
        # Strip a trailing extension like (V.O.) / （画外音）.
        name = re.sub(r"[（(].*[）)]\s*$", "", name).strip()
        return name or None
    # Latin all-caps cue.
    core = re.sub(r"[（(].*[）)]\s*$", "", s).strip()
    if core and _HAS_UPPER.search(core) and not _HAS_LOWER.search(core):
        return core
    return None


def parse_fountain(text: str) -> FountainParseResult:
    """Parse a manuscript into structural elements with source spans.

    Offsets are character indices into ``text`` (0-indexed, end exclusive).
    """
    result = FountainParseResult()
    seen_characters: set[str] = set()

    # Walk line by line, tracking the running character offset.
    offset = 0
    pending_character: str | None = None
    # Track whether the previous non-handled position was blank (for cue rules).
    prev_blank = True

    lines = text.splitlines(keepends=True)
    for raw in lines:
        line = raw.rstrip("\r\n")
        stripped = line.strip()
        line_start = offset
        # Span covers the visible text only (exclude leading/trailing ws span
        # drift is acceptable for MVP; we use the trimmed content bounds).
        content_start = line_start + (len(line) - len(line.lstrip()))
        content_end = content_start + len(stripped)
        offset += len(raw)

        if not stripped:
            pending_character = None
            prev_blank = True
            continue

        # Scene heading.
        if _is_scene_heading(line):
            text_val = stripped[1:].strip() if stripped.startswith(".") and not stripped.startswith("..") else stripped
            result.elements.append(
                FountainElement(
                    ElementType.SCENE_HEADING, text_val, content_start, content_end
                )
            )
            pending_character = None
            prev_blank = False
            continue

        # Character cue: only valid when preceded by a blank line.
        cue = _cue_name(line) if prev_blank else None
        if cue is not None:
            result.elements.append(
                FountainElement(
                    ElementType.CHARACTER, cue, content_start, content_end
                )
            )
            if cue not in seen_characters:
                seen_characters.add(cue)
                result.characters.append(cue)
            pending_character = cue
            prev_blank = False
            continue

        # Parenthetical under a cue.
        if pending_character and _PAREN_LINE.match(stripped):
            result.elements.append(
                FountainElement(
                    ElementType.PARENTHETICAL,
                    stripped,
                    content_start,
                    content_end,
                    character=pending_character,
                )
            )
            prev_blank = False
            continue

        # Dialogue: a line attributed to the pending character.
        if pending_character:
            result.elements.append(
                FountainElement(
                    ElementType.DIALOGUE,
                    stripped,
                    content_start,
                    content_end,
                    character=pending_character,
                )
            )
            prev_blank = False
            continue

        # Otherwise: action.
        result.elements.append(
            FountainElement(ElementType.ACTION, stripped, content_start, content_end)
        )
        prev_blank = False

    return result
