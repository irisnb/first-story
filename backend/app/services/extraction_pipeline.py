"""Shared extraction pipeline (tasks group 4).

A single entry point both the editor save path (committed/document) and the
dialogue adoption / candidate path (candidate/chat) call through, so extraction
behavior never diverges between the two lanes.

The pipeline is ALWAYS failure-isolated: any stage raising must never propagate
back to the caller and never block the user's writing. The candidate lane is an
"idea record" - it stamps ``acceptance_status=candidate`` and the underlying
ExtractionService already withholds committed-world entity events
(``character.created`` / ``batch.committed``) and the alias-resolution pass is
skipped (no global who-is-who writes for a tentative idea).
"""

from __future__ import annotations

import logging

from .project import ProjectService

logger = logging.getLogger("first_story.extraction")


def run_extraction_pipeline(
    project_service: ProjectService,
    project_id: str,
    *,
    content: str,
    source_type: str = "document",
    source_id: str = "",
    acceptance_status: str = "committed",
) -> None:
    """Run extraction (+ alias + contradiction for committed) then reproject.

    Args:
        source_type: "document" (editor prose) or "chat" (dialogue brainstorm).
        source_id: revision id for document, message id for chat - threaded into
            ``source_revision`` so facts trace back to their origin.
        acceptance_status: "committed" or "candidate". Candidate skips the global
            alias-resolution pass and contradiction detection entirely.

    Every stage is isolated; failures are logged and swallowed.
    """
    is_candidate = acceptance_status == "candidate"
    try:
        extraction = project_service.get_extraction_service(project_id)
        if extraction is None:
            return
        extraction.extract(
            content,
            revision=source_id,
            acceptance_status=acceptance_status,
            source_type=source_type,
        )

        # The alias pass writes GLOBAL who-is-who identity bindings. A candidate
        # idea must never mutate that global table, so skip it for candidates.
        if not is_candidate:
            try:
                alias_resolver = project_service.get_alias_resolver_service(project_id)
                if alias_resolver is not None:
                    alias_resolver.resolve(content)
            except Exception as exc:  # noqa: BLE001 - alias pass must never block writing
                logger.warning("alias resolution failed: %s", exc)

            # Contradiction detection runs only over committed facts. Skip the
            # whole pass for candidate writes - a hypothesis is never flagged.
            try:
                contradiction = project_service.get_contradiction_service(project_id)
                if contradiction is not None:
                    contradiction.run_batch(revision=source_id)
            except Exception as exc:  # noqa: BLE001 - monitor must never block writing
                logger.warning("contradiction batch failed: %s", exc)

        services = project_service.get_services(project_id)
        if services:
            _, projector = services
            projector.rebuild()
    except Exception as exc:  # noqa: BLE001 - never let pipeline work crash a caller
        logger.warning("extraction pipeline failed: %s", exc)
