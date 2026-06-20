"""Screenplay export - render the current manuscript as Fountain or plain text.

Implements the export half of the screenplay-import-export spec. (Import is the
ordinary save path: pasted text becomes a ``document.revised`` revision and runs
the same Fountain parse + extraction as hand-written prose.)

- ``to_fountain``: returns the manuscript with its Fountain structure intact.
  The stored manuscript is already Fountain, so this is a faithful pass-through.
- ``to_plain_text``: strips Fountain authoring markers to a clean reading text:
  - drops the ``@`` forced-cue prefix on character names,
  - drops the leading ``.`` on forced scene headings,
  - keeps scene headings, cues, parentheticals, dialogue and action as readable
    lines, with blank lines separating blocks.
"""

from __future__ import annotations

from .fountain import ElementType, parse_fountain


def to_fountain(content: str) -> str:
    """Export keeping Fountain syntax structure (faithful pass-through)."""
    return content


def to_plain_text(content: str) -> str:
    """Export a clean, marker-free reading text rendered from structure."""
    parsed = parse_fountain(content)
    lines: list[str] = []
    prev_type: ElementType | None = None

    for el in parsed.elements:
        # Separate a new scene or a new speaker block with a blank line.
        if prev_type is not None and el.type in (
            ElementType.SCENE_HEADING,
            ElementType.CHARACTER,
            ElementType.ACTION,
        ):
            if lines and lines[-1] != "":
                lines.append("")

        if el.type is ElementType.CHARACTER:
            # el.text already has '@' stripped by the parser.
            lines.append(el.text)
        elif el.type is ElementType.SCENE_HEADING:
            # el.text already has a forced-heading leading '.' stripped.
            lines.append(el.text)
        else:
            lines.append(el.text)

        prev_type = el.type

    return "\n".join(lines).strip() + ("\n" if lines else "")
