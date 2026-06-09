## 1. Paper Walkthrough

- [ ] 1.1 Create `walkthrough.md` for the case “姐姐十年前死亡却昨天打电话”.
- [ ] 1.2 Show the `SystemEvent` entries that introduce the death fact, later phone-call fact, continuity finding, and user response.
- [ ] 1.3 Show the rebuilt `story_state` projection after replaying those events.
- [ ] 1.4 Show the `ContinuityEvent` evidence chain from finding to `Fact` to `SystemEvent`.
- [ ] 1.5 Show how ignore / accept / keep choices update continuity status and `UserPreference` without deleting evidence.

## 2. Spec Review

- [ ] 2.1 Review `specs/event-log/spec.md` against `walkthrough.md` and tighten requirements that fail the walkthrough.
- [ ] 2.2 Review `specs/minimal-story-state/spec.md` against `walkthrough.md` and tighten fields that fail the walkthrough.
- [ ] 2.3 Review `design.md` for scope creep and remove UI, real LLM, LightRAG, full technology stack, or multi-Agent implementation details.

## 3. Validation

- [ ] 3.1 Run `openspec validate define-minimal-story-state-and-event-log` and fix any validation errors.
- [ ] 3.2 Run `openspec status --change define-minimal-story-state-and-event-log` and confirm all artifacts are complete.
- [ ] 3.3 Summarize remaining open questions that should move to later changes rather than blocking this foundation change.