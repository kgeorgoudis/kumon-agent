# Data Model - First Working Version (V1)

## Entities

### ChildProfile
- **Purpose**: Stores parent-configurable child settings for worksheet generation.
- **Fields**:
  - `child_id` (str, unique)
  - `display_name` (str)
  - `age` (int)
  - `grade_level` (int)
  - `locale` (str, default `el-GR`)
  - `language` (str, default `el`)
  - `preferred_sheet_length` (int)
  - `timing_enabled` (bool)
  - `review_mix_ratio` (float)
  - `notes` (str)
  - `created_at` (datetime)
  - `updated_at` (datetime)

### Exercise
- **Purpose**: Deterministically generated math problem and answer pair.
- **Fields**:
  - `exercise_id` (str, unique)
  - `operand_a` (int|float)
  - `operand_b` (int|float)
  - `operator` (`+`, `−`, `×`, `÷`)
  - `answer` (int|float, Python-computed)
  - `problem_text` (str)
  - `answer_text` (str)
  - `micro_skill_id` (enum)

### WorksheetInstance
- **Purpose**: Captures one generated worksheet and answer key output.
- **Fields**:
  - `instance_id` (str, unique)
  - `child_id` (nullable str)
  - `micro_skill_id` (enum)
  - `worksheet_type` (enum)
  - `exercises` (list[Exercise])
  - `title_el` (str)
  - `instructions_el` (str)
  - `created_at` (datetime)
  - `html_path` (nullable str)
  - `answer_key_path` (nullable str)
  - `seed` (nullable int)

### MicroSkillMeta
- **Purpose**: In-app skill documentation and hierarchy data.
- **Fields**:
  - `micro_skill_id` (enum)
  - `parent_skill_id` (enum)
  - `name_en` / `name_el` (str)
  - `description_en` / `description_el` (str)
  - `difficulty_level` (int 1-10)
  - `prerequisites` (list[micro_skill_id])

## Relationships
- `ChildProfile (1) -> (N) WorksheetInstance`
- `WorksheetInstance (1) -> (N) Exercise`
- `Exercise (N) -> (1) MicroSkillMeta` via `micro_skill_id`

## Persistence Notes
- `child_profiles` and `worksheet_instances` stored in SQLite.
- `WorksheetInstance.exercises` persisted as JSON in v1 for simplicity.
- Inserts should be idempotent where feasible for CLI retries.

