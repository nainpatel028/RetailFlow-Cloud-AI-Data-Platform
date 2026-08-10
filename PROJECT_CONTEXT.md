# Project Context

This file tracks the current state of the project so any contributor (human
or AI) can quickly understand what phase the work is in.

## Current phase

**Session 1 — Foundation.** The repository structure, governance
documentation, data contracts, and the synthetic data generator are being
established. No ingestion, transformation, cloud, dashboard, or agent code
exists yet.

## Ticket status

| Ticket  | Description                        | Status                                   |
|---------|-------------------------------------|-------------------------------------------|
| RF-001  | Define MVP data model               | Done once this scaffolding is verified    |
| RF-002  | Build local Bronze ingestion        | Next                                      |
| —       | Silver / Gold transformations       | Planned                                   |
| —       | Data-quality audit engine           | Planned                                   |
| —       | Azure implementation                | Planned                                   |
| —       | Power BI dashboards                 | Planned                                   |
| —       | n8n read-only AI operations agent   | Planned                                   |
| —       | AWS port                            | Planned                                   |
| —       | CI/CD and monitoring                | Planned                                   |

## What exists today

- Repository scaffolding (this session)
- Documentation: business requirements, architecture, data contracts, cloud
  mapping notes, Power BI scope, agentic AI scope
- A deterministic synthetic data generator producing realistically dirty
  raw source data (Parquet, Snappy-compressed) as `development` and
  `portfolio` profiles under `data/incoming/` — see
  [DECISIONS.md](DECISIONS.md) #009
- Test suite validating the generator's output

## What does not exist yet

- Any database or SQL DDL
- Any Bronze/Silver/Gold transformation code
- Any data-quality execution engine
- Any Azure or AWS resources
- Any n8n workflow or agent
- Any Power BI file
- Any CI/CD workflow

See [TASK_BOARD.md](TASK_BOARD.md) for ticket sequencing and
[DECISIONS.md](DECISIONS.md) for why the project is structured this way.
