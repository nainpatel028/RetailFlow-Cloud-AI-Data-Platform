# n8n Orchestration

**Status: NOT IMPLEMENTED.**

## Future purpose

Will hold the n8n workflow definitions for the read-only operations agent
described in [docs/agentic_ai_scope.md](../../docs/agentic_ai_scope.md),
once RF-009 (read-only agent) and RF-010 (human-approval action flow)
begin.

## Learning objectives

- Building an n8n workflow that answers natural-language questions from
  pipeline/data-quality state
- Designing a scoped, read-only tool allowlist for an LLM node
- Adding a human-approval gate before any workflow step with an external
  effect

No workflow exports, deployment instructions, or credentials are provided
here — none exist yet. See [DECISIONS.md](../../DECISIONS.md) #005 for the
read-only-first guardrail this design must follow.
