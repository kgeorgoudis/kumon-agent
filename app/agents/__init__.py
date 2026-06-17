"""
Agents layer — LangGraph orchestration for LLM-assisted tasks.

Constitutional boundaries
-------------------------
Good uses of the LLM (Constitutional Principle I):
  - Explain a mistake in simple Greek
  - Summarise a worksheet result for the parent
  - Classify ambiguous handwriting / OCR edge cases
  - Draft next-step rationale

Bad uses (prohibited):
  - Compute arithmetic answers
  - Make progression decisions without deterministic rules
  - Replace the scoring engine
"""

