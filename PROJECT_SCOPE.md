# Project Scope

## In scope

- Three synthetic datasets: `customers`, `orders`, `payments`, generated as
  realistically dirty raw source data (development and portfolio profiles —
  see [docs/data_contracts.md](docs/data_contracts.md))
- A local pipeline (Python + SQL, run on a laptop, no cloud dependency)
- A medallion architecture (Bronze preserves raw records → Silver validates,
  casts, standardizes, deduplicates, and quarantines invalid rows → Gold
  holds analytics-ready business models)
- A data-quality audit layer, exercised against the deliberately dirty
  source profiles
- An Azure implementation of the pipeline, including Snowflake-style
  multi-file COPY INTO ingestion patterns against the portfolio profile
- Power BI dashboards answering the business questions in
  [README.md](README.md)
- A read-only n8n operations agent that can *observe and report*, with any
  action requiring explicit human approval
- An AWS port of the Azure implementation, to compare cloud approaches
- Testing, monitoring, and CI/CD across the implemented components

## Out of scope

- Real customer, order, or payment data of any kind
- Production deployment or serving real business traffic
- Autonomous data modification by the AI agent (no writes without a human
  approving first)
- High-volume or streaming ingestion (this platform is batch, small-scale,
  and learner-paced)
- Enterprise-grade availability, disaster recovery, or SLA guarantees
- Any claim that this project reflects a real production banking or retail
  system

## Why this scope

The project is sized to be buildable and understandable by one learner over
tens of hours, not hundreds. Scope is kept intentionally narrow so each
component can be built, tested, and explained rather than generated in bulk.
See [LEARNING_PLAN.md](LEARNING_PLAN.md) for how that constraint shapes the
work, and [DECISIONS.md](DECISIONS.md) for the specific tradeoffs made.
