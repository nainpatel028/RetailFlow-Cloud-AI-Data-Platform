# Agent Rules

These rules apply to any AI agent (Claude Code or otherwise) working in this
repository. See [LEARNING_PLAN.md](LEARNING_PLAN.md) for the reasoning
behind them.

## Required behavior

1. **Explain before implementing.** Describe the approach and get
   confirmation before writing non-trivial code, especially for core
   learning tickets.
2. **Do not generate core learning-ticket solutions before the user
   attempts them.** Scaffolding, fixtures, tests, and documentation are fair
   game for AI assistance. Ingestion logic, transformation SQL, cloud
   resource configuration, and agent workflow logic are the user's to
   attempt first.
3. **Never modify unrelated files.** Changes should be scoped to the task at
   hand.
4. **Never stage, commit, or push without explicit approval** for that
   specific action. A prior approval does not carry forward to later
   changes.
5. **Never store secrets or personal paths.** No real credentials, API keys,
   connection strings, or machine-specific absolute paths in any tracked
   file. Use `.env` (untracked) and `.env.example` (placeholders only).
6. **Use feature branches for implementation tickets.** Do not commit
   ticket implementation work directly to `main`.
7. **Run tests and report evidence.** When code changes are made, run the
   relevant test suite and report actual results — not an assumption that
   it passed.
8. **Preserve user changes.** Do not overwrite or discard in-progress user
   work without checking first.
9. **Clearly separate completed and planned work** in documentation and
   status updates. Never describe a planned component as if it already
   exists.

## Scope reminder

This project explicitly excludes, until their dedicated tickets: data
ingestion code, SQL database tables, Bronze/Silver/Gold transformations, a
data-quality execution engine, Azure/AWS resources, n8n workflows, Power BI
files, and CI/CD workflows. See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) and
[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) for current status.
