# Agentic AI Scope (Planned)

**Status: NOT IMPLEMENTED.** No n8n workflow, agent, or LLM integration
exists yet. This document records the intended scope and guardrails for
when this work begins (RF-009/RF-010).

## Purpose

An operations agent that can answer natural-language questions about
pipeline and data-quality state — e.g., "did last night's ingestion run
succeed?", "how many rows failed validation this week?", "what's our
current payment-failure rate?" — without a human writing SQL by hand.

## Guardrails (see [DECISIONS.md](../DECISIONS.md) #005)

- **Read-only by default.** The agent can query pipeline run metadata,
  data-quality audit results, and Gold-layer aggregates. It cannot write to
  any data store.
- **No autonomous external actions.** Any action with an external effect
  (rerunning a pipeline, sending a notification, modifying data) requires a
  specific human approval at the time of the action — a standing approval
  does not authorize future actions.
- **Scoped tool access.** The agent's available tools/queries will be an
  explicit allowlist, not open database access.
- **No production data.** The agent only ever operates over this project's
  synthetic datasets.

## Planned phasing

1. **RF-009 — Read-only agent.** Observe and report only. No action
   capability at all.
2. **RF-010 — Human-approval action flow.** Introduce a narrow set of
   proposable actions (e.g., "rerun ingestion"), each requiring explicit
   approval before execution, with the approval and the action both logged.

## Learning objectives

- Designing a tool/function allowlist for an LLM agent
- Building a human-in-the-loop approval step in n8n
- Reasoning about blast radius before granting an agent any write capability
