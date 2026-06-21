## ADDED Requirements

### Requirement: Classify content endpoint

The system SHALL provide an endpoint `POST /api/v1/projects/{project_id}/classify` to classify user content into modules and sections.

#### Scenario: Classify character information

- **WHEN** client sends content "主角叫小红，是一名社畜，女 26岁"
- **THEN** the system returns classification with module="character", section="主要角色", confidence > 0.8

#### Scenario: Classify world building information

- **WHEN** client sends content "这个世界存在上班族群体，还有怨念具象化的怪物"
- **THEN** the system returns classification with module="world", section="社会结构"

### Requirement: Classification response format

The system SHALL return classifications in the following format:

```json
{
  "classifications": [
    {
      "module": "string (world|characters|plot|theme|structure)",
      "section": "string (section name in the module)",
      "content": "string (formatted content to append)",
      "confidence": "float (0.0-1.0)"
    }
  ]
}
```

#### Scenario: Multiple classifications

- **WHEN** content contains information for multiple modules
- **THEN** the system returns multiple classification entries

### Requirement: Classification context

The system SHALL include current module summaries as context for classification to maintain consistency.

#### Scenario: Context-aware classification

- **WHEN** classifying content about an existing character
- **THEN** the system uses existing character summary to improve accuracy

### Requirement: No classification option

The system MAY return an empty classifications array when content does not belong to any module.

#### Scenario: Content not classifiable

- **WHEN** content is "好的，我明白了" (acknowledgment without story content)
- **THEN** the system returns empty classifications array

### Requirement: Classification triggered after dialogue

The system SHALL trigger classification automatically after each candidate message is processed by the dialogue agent.

#### Scenario: Auto-classify after dialogue

- **WHEN** dialogue agent processes a candidate message
- **THEN** classification API is called in the background
- **AND** results are appended to the appropriate module documents
