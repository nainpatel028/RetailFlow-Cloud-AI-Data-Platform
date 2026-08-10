# RetailFlow Cloud AI Data Platform

RetailFlow is a fictional mid-size Canadian retailer that sells through online,
mobile, and in-store channels. This repository is a learning project that
builds, from scratch, the kind of data platform a retailer like RetailFlow
would use to understand its sales and payment operations — starting local and
small, then layering on cloud, orchestration, dashboards, and an AI operations
agent as the learner progresses through tickets.

**This is a personal learning project using entirely synthetic data.** No real
customers, orders, payments, or credentials are used anywhere in this
repository.

## The business problem

RetailFlow's leadership cannot currently answer basic operational questions
without manually pulling data from disconnected systems. This platform is
being built to answer:

- What is our daily revenue?
- How many orders are completed vs. cancelled?
- What is our payment-failure rate, and why are payments failing?
- Who are our highest-value customers?
- How reliable is our incoming data (are we missing fields, seeing orphaned
  records, or receiving bad values from source systems)?

## MVP datasets

The initial platform is intentionally small — three related tables:

| Dataset     | Grain                     | Primary key   |
|-------------|---------------------------|---------------|
| `customers` | One row per customer      | `customer_id` |
| `orders`    | One row per order         | `order_id`    |
| `payments`  | One row per payment attempt | `payment_id` |

See [docs/data_contracts.md](docs/data_contracts.md) for full column-level
definitions and [docs/business_requirements.md](docs/business_requirements.md)
for the data model and business questions.

**The incoming source data is intentionally dirty.** It models a raw
source-system export — duplicate and missing IDs, invalid dates, bad
amounts, orphaned foreign keys, and other realistic problems are injected
at low, configurable rates (most rows remain valid). Cleaning that data is
the explicit job of the future Silver layer, not the generator — see
[docs/data_contracts.md](docs/data_contracts.md) for the raw-vs-logical
type design and the full list of injected issue codes.

Source data is written as Snappy-compressed Parquet, in two profiles:

| Profile       | Purpose                              | customers | orders    | payments  |
|---------------|----------------------------------------|-----------|-----------|-----------|
| `development` | Fast local iteration                    | 10,000    | 100,000   | 130,000   |
| `portfolio`   | Snowflake / cloud-scale demonstrations  | 100,000   | 1,000,000 | 1,300,000 |

## Current implementation status

| Component                              | Status           |
|-----------------------------------------|------------------|
| Repository scaffolding & documentation  | ✅ Implemented   |
| Synthetic raw source-data generator (development + portfolio profiles, Parquet) | ✅ Implemented |
| Local Bronze ingestion                  | 🕒 Planned (RF-002) |
| Silver cleaning / casting / deduplication | 🕒 Planned       |
| Gold analytics-ready models             | 🕒 Planned       |
| Data-quality audit engine               | 🕒 Planned       |
| Azure implementation                    | 🕒 Planned       |
| Power BI dashboards                     | 🕒 Planned       |
| n8n read-only AI operations agent       | 🕒 Planned       |
| AWS port                                | 🕒 Planned       |
| CI/CD and monitoring                    | 🕒 Planned       |

No cloud resources, dashboards, pipelines, or AI agents exist yet. Everything
marked "Planned" is documentation and scaffolding only, to be built manually
in later tickets — see [TASK_BOARD.md](TASK_BOARD.md).

## Planned phases

1. **Local foundation** — Python, SQL, Docker, Git (this session)
2. **Bronze** — ingest raw Parquet as-is, preserving source values exactly
3. **Silver** — validate, cast (`TRY_CAST`/`TRY_TO_*`), standardize, deduplicate,
   and quarantine invalid rows; **Gold** — analytics-ready business models
4. **Azure implementation** of the pipeline (storage, compute, SQL)
5. **Power BI** dashboards answering the business questions
6. **n8n read-only agentic AI** operations agent, human-approved actions only
7. **AWS port** of the Azure implementation
8. **CI/CD and monitoring** across environments

## Repository layout

See [PROJECT_SCOPE.md](PROJECT_SCOPE.md) for what is in and out of scope, and
[docs/architecture.md](docs/architecture.md) for the target architecture
diagram with planned vs. implemented components labeled.

## Getting started (data generation only)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Fast, small profile for local iteration:
python scripts/generate_data.py --profile development

# Large profile for Snowflake / cloud-scale demos (slower, ~2.4M rows):
python scripts/generate_data.py --profile portfolio

pytest
```

This produces synthetic raw Parquet source files under `data/incoming/`,
one directory per dataset per profile, e.g.
`data/incoming/development/customers/part-00000.parquet`, plus a
`manifest.json` per profile documenting row counts, file hashes, and every
injected data-quality issue. No database, cloud, or dashboard setup is
required for this step. Regenerating requires `--overwrite` (or `--force`)
to avoid silently discarding existing output.

Generated Parquet files are **not** committed to git (they're regenerable
from the seed and the portfolio profile alone is millions of rows); each
profile's `manifest.json` is small and is tracked, documenting exactly what
running the generator should produce.

## Governance documents

- [PROJECT_SCOPE.md](PROJECT_SCOPE.md) — in/out of scope
- [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md) — current phase and status
- [TASK_BOARD.md](TASK_BOARD.md) — ticket tracking
- [DECISIONS.md](DECISIONS.md) — architectural decision log
- [LEARNING_PLAN.md](LEARNING_PLAN.md) — how this project is used to learn
- [AGENTS.md](AGENTS.md) — rules for AI-assisted work in this repo
