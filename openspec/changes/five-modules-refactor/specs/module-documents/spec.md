## ADDED Requirements

### Requirement: Module document storage

The system SHALL store five module documents as Markdown files in each project directory:
- `world.md` — World building
- `characters.md` — Character information
- `plot.md` — Plot structure
- `theme.md` — Themes and motifs
- `structure.md` — Narrative structure

#### Scenario: Create module documents on project creation

- **WHEN** a new project is created
- **THEN** the system creates all five module documents with default template content

#### Scenario: Read module document

- **WHEN** a client requests `GET /api/v1/projects/{project_id}/modules/{module}`
- **THEN** the system returns the Markdown content of the specified module

### Requirement: Module document structure

Each module document SHALL have a fixed section structure defined by templates:

- **world.md**: 总述, 魔法/技术系统, 社会结构, 地理, 时间线锚点, 细节记录
- **characters.md**: 总述, 主要角色, 次要角色, 角色关系
- **plot.md**: 总述, 主线, 支线, 关键事件
- **theme.md**: 总述, 核心主题, 次要主题
- **structure.md**: 总述, 幕布结构, 节奏设计, 关键转折点

#### Scenario: Parse module document sections

- **WHEN** the system parses a module document
- **THEN** it extracts content by section headers (## prefix)

### Requirement: Markdown parser

The system SHALL parse Markdown documents using markdown-it-py library to extract structured content.

#### Scenario: Parse section content

- **WHEN** the parser processes a module document
- **THEN** it returns a dictionary mapping section names to their content

### Requirement: Markdown renderer

The system SHALL render structured content back to Markdown format.

#### Scenario: Append list item to section

- **WHEN** the system needs to add content to a section
- **THEN** it appends a new list item (`- content`) to that section

#### Scenario: Update module document

- **WHEN** a client sends `PUT /api/v1/projects/{project_id}/modules/{module}` with new content
- **THEN** the system validates the structure and saves the document
