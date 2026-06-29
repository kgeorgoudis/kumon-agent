# Feature Specification: Improve Greek LLM Response Quality

**Feature Branch**: `009-greek-llm-quality`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "As a parent (operator) I want better responses from LLM in Greek when I run `uv run kumon progress -c <child_id>` commands. Currently I often get syntax mistakes or even hallucinations. The LLM I use is Qwen3-4B-MLX-4bit."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Grammatically Correct Greek Progress Summaries (Priority: P1)

As a parent, when I run `uv run kumon progress -c <child_id>`, I want the Greek narrative (`summary_el`) to be free of grammatical errors, broken syntax, and unnatural phrasing so that I can easily understand my child's progress.

**Why this priority**: The core value of the progress command is delivering clear, understandable Greek text to the parent. If the text contains syntax errors or unnatural phrasing, the feature fails its primary purpose regardless of other qualities.

**Independent Test**: Can be fully tested by running the progress command and evaluating the returned `summary_el` text for grammatical correctness and readability. Delivers clear, actionable parent communication.

**Acceptance Scenarios**:

1. **Given** a child with at least 3 graded worksheets, **When** the parent runs the progress command, **Then** the returned `summary_el` text uses correct Greek grammar (subject-verb agreement, proper case declensions, correct article usage)
2. **Given** a child with progress data, **When** the progress command generates a narrative, **Then** the text reads naturally to a native Greek speaker without awkward machine-translated phrasing
3. **Given** any valid child profile, **When** the progress command is run multiple times, **Then** the Greek output consistently maintains grammatical correctness across runs

---

### User Story 2 - Elimination of Hallucinated Content (Priority: P1)

As a parent, I want the LLM-generated narrative to contain only statements grounded in the actual worksheet data, with no invented facts, skills, scores, or recommendations that contradict the deterministic metrics.

**Why this priority**: Hallucinations (fabricated data, non-existent skills, invented scores) directly undermine parent trust and can lead to incorrect educational decisions. This is equally critical as grammar quality.

**Independent Test**: Can be tested by comparing the LLM narrative output against the deterministic data payload to verify every claim in the text is traceable to actual input data.

**Acceptance Scenarios**:

1. **Given** a child with specific worksheet history, **When** the progress narrative is generated, **Then** every skill mentioned in `summary_el` exists in the provided data payload
2. **Given** a child's progress data, **When** the LLM generates suggestions, **Then** each `target_micro_skill_id` is either present in the child's history or in the `next_skill_options` provided
3. **Given** a child with a declining trend, **When** the narrative is generated, **Then** the text does not claim improvement or stability

---

### User Story 3 - Reliable JSON Output Structure (Priority: P2)

As a parent, I want the progress command to never fail due to malformed LLM output, so that I always receive a usable progress report even when the small model struggles with output formatting.

**Why this priority**: A small 4-bit quantized model may occasionally produce malformed JSON or extra text around the JSON. The system should handle this gracefully rather than crashing.

**Independent Test**: Can be tested by running the progress command repeatedly and verifying it always returns a valid report (either full narrative or graceful degradation).

**Acceptance Scenarios**:

1. **Given** any valid progress data, **When** the LLM produces output with extra text around the JSON, **Then** the system extracts valid JSON and returns a complete report
2. **Given** the LLM produces completely invalid output, **When** the system detects the failure, **Then** the report degrades gracefully with deterministic metrics and a clear status indicator
3. **Given** any progress command execution, **When** the report is returned, **Then** it always contains all deterministic fields (accuracy, trend, skill list) regardless of LLM success

---

### Edge Cases

- What happens when the LLM returns Greek text mixed with English fragments or code?
- How does the system handle responses where the model repeats the prompt back instead of generating new content?
- What happens when the model produces valid JSON but with empty string values for Greek fields?
- How does the system behave when the model generates excessively long responses that exceed expected length?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST produce Greek narrative text (`summary_el`) that is grammatically correct and uses natural phrasing appropriate for a parent audience
- **FR-002**: System MUST ensure every factual claim in the generated narrative is traceable to data present in the deterministic context payload
- **FR-003**: System MUST never mention micro-skills, scores, or trends that are absent from the provided input data
- **FR-004**: System MUST extract valid JSON from LLM output even when the response contains surrounding text, markdown fencing, or trailing content
- **FR-005**: System MUST degrade gracefully when the LLM produces unusable output, falling back to deterministic-only reporting with appropriate status codes
- **FR-006**: System MUST validate that suggested `target_micro_skill_id` values exist either in the child's history or in the `next_skill_options` set before including them in the report
- **FR-007**: System MUST keep generated Greek text concise (2-3 sentences for summary, 1-2 sentences per suggestion rationale) to stay within the quality ceiling of the small model

### Key Entities *(include if feature involves data)*

- **Progress Narrative**: The Greek-language summary text generated for the parent, consisting of `summary_el` (qualitative overview) and per-suggestion `rationale_el` (justification grounded in data)
- **Deterministic Context Payload**: The structured data (skills, accuracy, trends, next options) provided to the LLM as the sole factual basis for narrative generation
- **Validation Gate**: A post-generation check that verifies LLM output against the input data to catch hallucinations and structural errors before presenting to the parent

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of generated `summary_el` texts pass a Greek grammar validation check (no broken syntax, correct declensions, proper sentence structure)
- **SC-002**: 100% of factual claims in generated narratives are traceable to the provided deterministic data (zero hallucinated skills, scores, or trends)
- **SC-003**: The progress command produces a usable report (either full narrative or graceful degradation) in 100% of executions — never crashes due to LLM output issues
- **SC-004**: Parent can read and understand the progress summary without confusion or need for interpretation in under 30 seconds

## Assumptions

- The LLM model in use (Qwen3-4B-MLX-4bit) is a small, quantized model with known limitations in following complex instructions and producing consistent structured output
- Prompt engineering and output validation are the primary levers for quality improvement (model change is not in scope)
- The existing prompt structure (persona + task block) is the right architecture and will be refined rather than replaced
- Greek language quality issues stem from the model's limited capacity rather than incorrect prompting language
- The system already has graceful degradation infrastructure (narrative_status, llm_error_code) that can be extended
- Few-shot examples in the prompt may significantly help a small model produce correct Greek and valid JSON
- Keeping prompts shorter and more constrained will produce better results from a 4B parameter model than longer, more detailed prompts

