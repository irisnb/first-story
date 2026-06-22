"""Chat / dialogue API (tasks group 7).

Three endpoints, all under a project:

- ``POST /chat`` - one dialogue turn. Returns ``{reply, message_id, intent,
  extraction_status}``. The response carries NO continuity/contradiction
  evidence and NO LLM key - evidence is still rendered only via the ``/state``
  poll into the evidence column. A ``candidate`` turn schedules a candidate
  extraction as a background task so the reply is never blocked.

- ``POST /manuscript/adopt`` - the ONLY way chat content enters the manuscript.
  Appends the selected text to the END of the manuscript and re-extracts it in
  ``committed`` mode (producing NEW committed facts; old candidate facts are
  left untouched). The read-modify-write runs inside the Hub per-project lock
  and is idempotent on ``adopt_request_id`` so a double-click never double-appends.

- style-memo endpoints - add / archive / list global creative-direction notes.
  A memo is asked-then-stored by the UI; archived, never deleted.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..services import ProjectService
from ..services.hub import get_hub

if TYPE_CHECKING:
    from ..models.state import StoryState

logger = logging.getLogger("first_story.chat")

# Context summary trigger thresholds (must match dialogue.py)
_MINOR_SUMMARY_TURNS = 10  # Every 10 turns: update recent_focus
_MAJOR_SUMMARY_TURNS = 30  # Every 30 turns: update all fields

router = APIRouter(prefix="/projects/{project_id}")


def get_project_service() -> ProjectService:
    """Dependency injection for ProjectService."""
    from ..config import get_settings

    settings = get_settings()
    return ProjectService(settings.projects_root)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------- chat


class ChatRequest(BaseModel):
    """A user chat message."""

    message: str = Field(..., description="User's chat message text")


class ChatResponse(BaseModel):
    """Dialogue turn result. Contains NO evidence and NO LLM key."""

    reply: str
    message_id: str
    intent: str
    extraction_status: str
    script_ready: bool = False  # Whether content is close to script format


def _run_candidate_extraction(
    project_service: ProjectService,
    project_id: str,
    content: str,
    source_id: str,
) -> None:
    """Background candidate extraction for a chat brainstorm.

    Delegates to the shared pipeline in candidate/chat mode (idea record only:
    no character/batch events, alias + contradiction skipped). Failure-isolated.
    """
    from ..services.extraction_pipeline import run_extraction_pipeline

    run_extraction_pipeline(
        project_service,
        project_id,
        content=content,
        source_type="chat",
        source_id=source_id,
        acceptance_status="candidate",
    )


def _run_context_summary_update(
    project_service: ProjectService,
    project_id: str,
    summary_type: str,
    current_turn_count: int,
) -> None:
    """Background context summary update.

    Generates summary, writes event, and rebuilds projection.
    Failure-isolated: errors are logged but not raised.

    Args:
        project_service: Project service instance
        project_id: Project ID
        summary_type: "minor" or "major"
        current_turn_count: Current turn count
    """
    from ..services.dialogue import DialogueAgent

    summary_service = project_service.get_context_summary_service(project_id)
    if summary_service is None:
        logger.warning("Cannot update context summary: project not found")
        return

    # Get story state summary for major summaries
    story_state_summary = ""
    if summary_type == "major":
        services = project_service.get_services(project_id)
        if services:
            _, projector = services
            state = projector.load_state()
            if state:
                # Build a simple summary of story state
                story_state_summary = DialogueAgent._state_summary(state)

    summary_service.update_and_persist(
        summary_type=summary_type,
        current_turn_count=current_turn_count,
        story_state_summary=story_state_summary,
    )


def _run_classification(
    project_service: ProjectService,
    project_id: str,
    content: str,
    state: Optional["StoryState"],
) -> None:
    """Background classification for module documents.

    Classifies content into modules/sections and appends to module documents.
    Failure-isolated: errors are logged but not raised.

    Args:
        project_service: Project service instance
        project_id: Project ID
        content: User content to classify
        state: Current story state for context
    """
    import asyncio
    from ..services.classify import ClassifyService
    from ..services.llm_provider import get_provider_for_slot

    try:
        # Get module document service
        module_service = project_service.get_module_document_service(project_id)
        if module_service is None:
            logger.warning("Cannot classify: module service not found")
            return

        # Get LLM provider for utility slot
        llm = get_provider_for_slot(project_id, "utility", project_service)

        # Get context summaries
        world_summary = ""
        character_summary = ""
        plot_summary = ""
        if state and state.story and state.story.context_summary:
            cs = state.story.context_summary
            world_summary = cs.world_brief
            character_summary = cs.character_brief
            plot_summary = cs.plot_brief

        # Run classification
        classify_service = ClassifyService(llm_provider=llm)
        result = asyncio.run(classify_service.classify(
            content=content,
            world_summary=world_summary,
            character_summary=character_summary,
            plot_summary=plot_summary,
        ))

        # Append to module documents
        for classification in result.classifications:
            success, message = module_service.system_append(
                module_name=classification.module,
                section_name=classification.section,
                content=classification.content,
            )
            if success:
                logger.info(
                    "Classified content to %s/%s: %s",
                    classification.module,
                    classification.section,
                    message,
                )
            else:
                logger.warning(
                    "Failed to classify to %s/%s: %s",
                    classification.module,
                    classification.section,
                    message,
                )

    except Exception as e:
        logger.warning("Classification failed: %s", e)


def _run_idea_extraction(
    project_service: ProjectService,
    project_id: str,
    user_message: str,
    assistant_message: str,
    assistant_message_id: str,
) -> None:
    """Background idea card extraction.

    Calls LLM to judge and extract idea cards from conversation.
    Failure-isolated: errors are logged but not raised.

    Args:
        project_service: Project service instance
        project_id: Project ID
        user_message: User's message content
        assistant_message: Assistant's reply content
        assistant_message_id: Assistant message ID for deduplication
    """
    import json
    from ..services.llm_provider import get_provider_for_slot

    try:
        # 1. Get LLM provider for utility slot
        llm = get_provider_for_slot(project_id, "utility", project_service)
        if llm is None:
            logger.warning("Cannot extract idea: LLM not configured")
            return

        # 2. Build prompt
        prompt = f"""你是创意识别助手。分析对话，判断是否包含值得用户保存的内容。

【创意的定义】
值得保存的内容包括：
• 原创、有价值的想法、隐喻、画面、洞见
• 可以被进一步发展的"种子"
• 有意味的设定、名字（如果有说法）
• 具体的、可触摸的细节
• 用户提供的设定（角色背景、世界观等）

不是创意：
• 纯粹的建议清单（除非清单项有原创洞见）
• 通用的写作技巧讲解（除非有原创例子）
• 分析框架、选项梳理（用户的最终决定才算）
• 过渡语、确认性问题

【注意】
• 宁可多收录，也不要漏掉有价值内容
• 如果有具体例子，只保留例子，跳过通用讲解

【输出格式】
输出一行 JSON，格式如下：
{{"is_idea": true/false, "summary": "一句话概括（20字以内）", "content": "提炼后的内容"}}

【对话】
用户：{user_message}
助手：{assistant_message}"""

        # 3. Call LLM
        response = llm.complete(prompt, temperature=0.3)
        raw_text = response.text.strip()
        
        # Debug log
        logger.info("Idea extraction LLM response: %s", raw_text[:500])

        # 4. Parse result
        # Try to extract JSON from the response
        try:
            # Find JSON in response - handle various formats
            # Try to find JSON object
            import re
            
            # Method 1: Find JSON object with regex
            json_match = re.search(r'\{[^{}]*"is_idea"[^{}]*\}', raw_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Method 2: Find first { and last }
                start = raw_text.find("{")
                end = raw_text.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = raw_text[start:end]
                else:
                    logger.warning("No JSON found in LLM response: %s", raw_text[:200])
                    return
            
            result = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response as JSON: %s, raw: %s", e, raw_text[:200])
            return

        is_idea = result.get("is_idea", False)
        if not is_idea:
            logger.info("LLM determined this is not an idea, skipping")
            return

        summary = result.get("summary", "")[:50]  # Limit summary length
        content = result.get("content", assistant_message)

        # 5. Check for duplicates
        project_dir = project_service.projects_root / project_id
        cards_file = project_dir / "idea_cards.json"

        if cards_file.exists():
            import json as json_module
            with open(cards_file, "r", encoding="utf-8") as f:
                existing_cards = json_module.load(f)
            for card in existing_cards:
                if card.get("source", {}).get("message_id") == assistant_message_id:
                    logger.info("Card already exists for message %s", assistant_message_id)
                    return
        else:
            existing_cards = []

        # 6. Create card
        from datetime import datetime, timezone
        from uuid import uuid4

        now = datetime.now(timezone.utc).isoformat()
        card_id = f"card_{uuid4().hex[:8]}"
        revision_id = f"rev_{uuid4().hex[:8]}"

        new_card = {
            "id": card_id,
            "current_revision_id": revision_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "source": {"message_id": assistant_message_id, "excerpt": content[:100]},
            "summary": summary,
            "created_from": "auto",
        }

        new_revision = {
            "revision_id": revision_id,
            "card_id": card_id,
            "content": content,
            "created_at": now,
        }

        # Load existing revisions
        revisions_file = project_dir / "idea_card_revisions.json"
        if revisions_file.exists():
            with open(revisions_file, "r", encoding="utf-8") as f:
                existing_revisions = json_module.load(f)
        else:
            existing_revisions = []

        # Save
        existing_cards.append(new_card)
        existing_revisions.append(new_revision)

        with open(cards_file, "w", encoding="utf-8") as f:
            json_module.dump(existing_cards, f, ensure_ascii=False, indent=2)

        with open(revisions_file, "w", encoding="utf-8") as f:
            json_module.dump(existing_revisions, f, ensure_ascii=False, indent=2)

        logger.info("Created idea card %s from message %s", card_id, assistant_message_id)

    except Exception as e:
        logger.warning("Idea extraction failed: %s", e)


@router.post("/chat", response_model=ChatResponse)
async def chat(
    project_id: str,
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    project_service: ProjectService = Depends(get_project_service),
) -> ChatResponse:
    """Run one dialogue turn through the Dialogue Agent (the single user voice).

    The agent persists the turn, classifies intent (ignore|candidate only), and
    returns the reply. A candidate turn queues a candidate extraction in the
    background - the reply returns before extraction finishes.
    """
    agent = project_service.get_dialogue_agent(project_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Inject the active style memos (creative direction) as background context.
    style_memos = project_service.get_style_memos(project_id)
    services = project_service.get_services(project_id)
    state = services[1].load_state() if services else None

    result = agent.respond(request.message, state=state, style_memos=style_memos)

    # candidate -> schedule extraction (never blocks the reply). The user's
    # original message text is the source content.
    if result.intent == "candidate" and result.llm_succeeded:
        background_tasks.add_task(
            _run_candidate_extraction,
            project_service,
            project_id,
            request.message,
            result.user_message_id,
        )
        # Also trigger classification for module documents
        background_tasks.add_task(
            _run_classification,
            project_service,
            project_id,
            request.message,
            state,
        )
        # Also trigger idea extraction
        background_tasks.add_task(
            _run_idea_extraction,
            project_service,
            project_id,
            request.message,
            result.reply,
            result.message_id,
        )

    # Check if context summary update should be triggered
    turn_count = result.turn_count
    if turn_count > 0 and turn_count % _MAJOR_SUMMARY_TURNS == 0:
        # Major summary at 30, 60, 90...
        logger.info("Triggering major context summary update at turn %d", turn_count)
        background_tasks.add_task(
            _run_context_summary_update,
            project_service,
            project_id,
            "major",
            turn_count,
        )
    elif turn_count > 0 and turn_count % _MINOR_SUMMARY_TURNS == 0:
        # Minor summary at 10, 20, 40, 50, 70, 80...
        # (but not at 30, 60, 90 which are major)
        logger.info("Triggering minor context summary update at turn %d", turn_count)
        background_tasks.add_task(
            _run_context_summary_update,
            project_service,
            project_id,
            "minor",
            turn_count,
        )

    return ChatResponse(
        reply=result.reply,
        message_id=result.message_id,
        intent=result.intent,
        extraction_status=result.extraction_status,
        script_ready=result.script_ready,
    )


# --------------------------------------------------------- chat history


class ChatMessage(BaseModel):
    """A single chat message from history."""

    message_id: str
    role: str = Field(..., description="user or assistant")
    content: str
    timestamp: str
    script_ready: bool = False  # Whether content is close to script format


class ChatMessageListResponse(BaseModel):
    """List of chat messages for a project."""

    messages: list[ChatMessage]
    total: int
    has_more: bool = Field(
        default=False, description="True if there are more messages before this range"
    )


@router.get("/chat/messages", response_model=ChatMessageListResponse)
async def get_chat_messages(
    project_id: str,
    limit: int = 50,
    before: str | None = None,
    project_service: ProjectService = Depends(get_project_service),
) -> ChatMessageListResponse:
    """Get chat messages for a project with pagination.

    Args:
        limit: Maximum number of messages to return (default 50)
        before: Message ID to get messages before (for loading older messages)

    Returns messages sorted by timestamp ascending (oldest first).
    """
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, _ = services

    # Use the indexed method for efficient pagination
    events, has_more = event_log.get_chat_messages(
        limit=limit,
        before_message_id=before,
    )

    messages: list[ChatMessage] = []
    for event in events:
        payload = event.payload
        messages.append(
            ChatMessage(
                message_id=payload.get("message_id", ""),
                role=payload.get("role", "user"),
                content=payload.get("content", ""),
                timestamp=event.timestamp.isoformat() if event.timestamp else "",
                script_ready=payload.get("script_ready", False),
            )
        )

    # Sort by timestamp ascending (oldest first)
    messages.sort(key=lambda m: m.timestamp)
    total = event_log.get_chat_message_count()
    return ChatMessageListResponse(messages=messages, total=total, has_more=has_more)


# --------------------------------------------------------------- adoption


class AdoptRequest(BaseModel):
    """Adopt chat content into the manuscript (append to end)."""

    content: str = Field(..., description="Selected text to append to the manuscript")
    adopt_request_id: str = Field(
        ..., description="Client-generated idempotency key (prevents double-append)"
    )
    adopted_from_message_id: str | None = Field(
        None, description="Source chat message id, for tracing committed facts back"
    )
    document_id: str = Field(default="main", description="Document identifier")


class AdoptResponse(BaseModel):
    """Result of an adoption."""

    revision_id: str
    duplicate: bool = Field(
        default=False, description="True if this was a recognized duplicate submission"
    )


def _run_committed_extraction(
    project_service: ProjectService,
    project_id: str,
    content: str,
    revision_id: str,
) -> None:
    """Background committed extraction over the adopted manuscript. Isolated."""
    from ..services.extraction_pipeline import run_extraction_pipeline

    run_extraction_pipeline(
        project_service,
        project_id,
        content=content,
        source_type="document",
        source_id=revision_id,
        acceptance_status="committed",
    )


@router.post("/manuscript/adopt", response_model=AdoptResponse)
async def adopt_into_manuscript(
    project_id: str,
    request: AdoptRequest,
    background_tasks: BackgroundTasks,
    project_service: ProjectService = Depends(get_project_service),
) -> AdoptResponse:
    """Append chat content to the manuscript end and re-extract in committed mode.

    The read-current -> append -> write sequence runs inside the Hub per-project
    write lock and is idempotent on ``adopt_request_id``: a double-click with the
    same key never appends twice. Old candidate facts are NEVER mutated - new
    committed facts are produced by re-extraction (append-only truth source).
    """
    doc_service = project_service.get_document_service(project_id)
    if doc_service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    event_log, projector = project_service.get_services(project_id)
    hub = get_hub()
    adopt_key = f"adopt:{request.adopt_request_id}"

    # The whole read-modify-write is atomic under the project lock.
    with hub.project_lock(event_log):
        # Idempotency: if this adopt_request_id already recorded an adoption,
        # do not append again (double-click guard).
        if event_log._check_idempotency(adopt_key) is not None:
            return AdoptResponse(revision_id="", duplicate=True)

        revisions = doc_service.list_revisions(document_id=request.document_id)
        current = revisions[-1].content if revisions else ""
        # Append the adopted text to the END of the manuscript.
        separator = "\n\n" if current.strip() else ""
        new_content = current + separator + request.content

        revision = doc_service.save_revision(
            new_content, document_id=request.document_id
        )

        # Record the adoption itself, carrying the source message for traceback.
        writer = hub.writer_for(event_log)
        writer.append(
            event_id=_new_id("evt"),
            idempotency_key=adopt_key,
            event_type="manuscript.adopted",
            payload={
                "revision_id": revision.revision_id,
                "document_id": request.document_id,
                "adopted_from_message_id": request.adopted_from_message_id,
                "adopt_request_id": request.adopt_request_id,
                "appended_span": {
                    "start": len(current) + len(separator),
                    "end": len(new_content),
                },
            },
            actor="user",
        )

    # Reproject (document text) immediately; committed extraction in background.
    projector.rebuild()
    project_service._update_project_timestamp(project_id)
    background_tasks.add_task(
        _run_committed_extraction,
        project_service,
        project_id,
        new_content,
        revision.revision_id,
    )
    return AdoptResponse(revision_id=revision.revision_id, duplicate=False)


# ------------------------------------------------------------- style memos


class StyleMemoRequest(BaseModel):
    """Add a global creative-direction note."""

    text: str = Field(..., description="Free-form creative direction (required)")
    kind: str | None = Field(None, description="Optional coarse tag (form/tone/...)")


class StyleMemoResponse(BaseModel):
    """A style memo as projected."""

    id: str
    text: str
    kind: str
    status: str


class StyleMemoListResponse(BaseModel):
    memos: list[StyleMemoResponse]


@router.get("/style-memos", response_model=StyleMemoListResponse)
async def list_style_memos(
    project_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> StyleMemoListResponse:
    """List all style memos (active and archived)."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    _, projector = services
    state = projector.load_state() or projector.rebuild()
    return StyleMemoListResponse(
        memos=[
            StyleMemoResponse(id=m.id, text=m.text, kind=m.kind, status=m.status)
            for m in state.story.style_memos
        ]
    )


@router.post("/style-memos", response_model=StyleMemoResponse, status_code=status.HTTP_201_CREATED)
async def add_style_memo(
    project_id: str,
    request: StyleMemoRequest,
    project_service: ProjectService = Depends(get_project_service),
) -> StyleMemoResponse:
    """Add a style memo (kind falls back to "未分类")."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, projector = services
    memo_id = _new_id("memo")
    writer = get_hub().writer_for(event_log)
    writer.append(
        event_id=_new_id("evt"),
        idempotency_key=f"creative_intent:{memo_id}",
        event_type="creative_intent.added",
        payload={"memo_id": memo_id, "text": request.text, "kind": request.kind},
        actor="user",
    )
    state = projector.rebuild()
    memo = next((m for m in state.story.style_memos if m.id == memo_id), None)
    if memo is None:  # pragma: no cover - just-written memo must exist
        raise HTTPException(status_code=500, detail="memo not projected")
    return StyleMemoResponse(id=memo.id, text=memo.text, kind=memo.kind, status=memo.status)


@router.post("/style-memos/{memo_id}/archive", response_model=StyleMemoResponse)
async def archive_style_memo(
    project_id: str,
    memo_id: str,
    project_service: ProjectService = Depends(get_project_service),
) -> StyleMemoResponse:
    """Archive a style memo (status -> archived; never deleted)."""
    services = project_service.get_services(project_id)
    if not services:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    event_log, projector = services
    writer = get_hub().writer_for(event_log)
    writer.append(
        event_id=_new_id("evt"),
        idempotency_key=f"creative_intent_archive:{memo_id}",
        event_type="creative_intent.archived",
        payload={"memo_id": memo_id},
        actor="user",
    )
    state = projector.rebuild()
    memo = next((m for m in state.story.style_memos if m.id == memo_id), None)
    if memo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style memo '{memo_id}' not found",
        )
    return StyleMemoResponse(id=memo.id, text=memo.text, kind=memo.kind, status=memo.status)
