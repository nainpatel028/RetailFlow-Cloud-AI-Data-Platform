# Claude Code Guidance

This file governs Claude Code's behavior in this repository. **Follow
[AGENTS.md](AGENTS.md) in full** — it is the authoritative rule set for any
AI agent working here; this file only adds Claude-specific notes.

## What Claude may generate

- Repository scaffolding (directory structure, config files, boilerplate)
- Synthetic data fixtures and the deterministic generator that produces them
- Repetitive configuration (e.g., `.gitignore`, dependency manifests)
- Tests
- Documentation

## What requires a user attempt first

Core learning-ticket implementation — ingestion logic, transformation SQL,
Bronze/Silver/Gold pipeline code, the data-quality execution engine, cloud
resource provisioning, orchestration workflows, and the n8n agent — is the
user's to attempt first, per [LEARNING_PLAN.md](LEARNING_PLAN.md) and
[AGENTS.md](AGENTS.md). Claude may review, explain, and help debug that
work once an attempt exists, and may scaffold the surrounding structure, but
should not produce the core solution unprompted.

## Current project state

See [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for what is implemented versus
planned before making any claims about project status.
