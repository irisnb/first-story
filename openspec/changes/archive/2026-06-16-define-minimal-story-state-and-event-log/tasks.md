## 1. Paper Walkthrough

- [x] 1.1 Create `walkthrough.md` for the case "姐姐十年前死亡却昨天打电话".
- [x] 1.2 Show the `SystemEvent` entries that introduce the death fact, later phone-call fact, continuity finding, and user response.
- [x] 1.3 Show the rebuilt `story_state` projection after replaying those events.
- [x] 1.4 Show the `ContinuityEvent` evidence chain from finding to `Fact` to `SystemEvent`.
- [x] 1.5 Show how ignore / resolve / explicit preference confirmation update continuity status and project preferences without deleting evidence.

## 2. Spec Review

- [x] 2.1 Review `specs/event-log/spec.md` against `walkthrough.md` and tighten requirements that fail the walkthrough.
- [x] 2.2 Review `specs/minimal-story-state/spec.md` against `walkthrough.md` and tighten fields that fail the walkthrough.
- [x] 2.3 Review `design.md` for scope creep and remove UI, real LLM, LightRAG, full technology stack, or multi-Agent implementation details.

## 3. Validation

- [x] 3.1 Run `openspec validate define-minimal-story-state-and-event-log` and fix any validation errors.
- [x] 3.2 Run `openspec status --change define-minimal-story-state-and-event-log` and confirm all artifacts are complete.
- [x] 3.3 Summarize remaining open questions that should move to later changes rather than blocking this foundation change.

## 4. Review Cleanup

- [x] 4.1 Fix the ignore flow so ignoring a continuity finding never confirms project lore or project preferences.
- [x] 4.2 Clarify that script documents are the source of truth for user prose, while event log is the source of truth for AI-structured state.
- [x] 4.3 Split `event_id` from `idempotency_key` and add batch metadata for extraction replay safety.
- [x] 4.4 Add Fact source anchors and lifecycle state so stale facts can be retracted or superseded.
- [x] 4.5 Split extraction confidence, contradiction confidence, delivery metadata, and possible explanations.
- [x] 4.6 Normalize JSON examples to `snake_case` and ASCII internal paths.
- [x] 4.7 Update summary, roadmap, and issue list after review cleanup.
