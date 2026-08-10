# Decisions

An architectural decision log. Each entry records a decision, its rationale,
and its status. Add new entries at the bottom; do not rewrite history.

## 001 — Three-table MVP data model

**Decision:** Start with exactly three datasets — `customers`, `orders`,
`payments` — rather than a fuller retail schema (products, inventory,
returns, etc.).

**Rationale:** Keeps every downstream layer (Bronze/Silver/Gold, data
quality, dashboards, agent) small enough to build and explain end-to-end
before adding breadth.

**Status:** Accepted.

## 002 — Defined grains and relationships

**Decision:** `customers` is one row per customer; `orders` is one row per
order (FK to `customers`); `payments` is one row per payment *attempt* (FK to
`orders`), allowing multiple payment attempts per order.

**Rationale:** Matches real-world retail behavior (a customer may retry a
failed payment) and gives the data-quality and payment-failure-rate use
cases something realistic to measure.

**Status:** Accepted. See [docs/business_requirements.md](docs/business_requirements.md).

## 003 — Azure-first, then AWS-port

**Decision:** Build the cloud implementation on Azure first, then port the
same design to AWS as a separate ticket.

**Rationale:** Learning goal is to understand one cloud deeply before
comparing services across providers, rather than building both in parallel
and understanding neither well.

**Status:** Accepted.

## 004 — Hybrid deterministic and agentic automation

**Decision:** Core pipeline stages (ingestion, transformation, quality
checks) are deterministic code. Only the operations layer (n8n) introduces
an LLM-driven agent, and only for observation/reporting.

**Rationale:** Deterministic, testable code is more appropriate for data
correctness; agentic behavior is reserved for the part of the system where
natural-language interaction adds real value (operational Q&A).

**Status:** Accepted.

## 005 — AI agent begins read-only with human approval

**Decision:** The n8n agent may query and summarize pipeline/data state, but
cannot take any action (rerun a job, modify data, send external
notifications) without explicit human approval at the time of the action.

**Rationale:** Avoids autonomous side effects while still being useful, and
keeps the learning focus on safe agent design.

**Status:** Accepted. See [docs/agentic_ai_scope.md](docs/agentic_ai_scope.md).

## 006 — Clean and quality-issues source profiles

**Decision:** The synthetic data generator produces two parallel profiles:
`clean` (fully valid) and `quality_issues` (same row counts, deliberate
documented anomalies).

**Rationale:** A data-quality layer is only meaningful if there is bad data
to catch. Keeping row counts equal between profiles makes the two profiles
directly comparable in tests and audits.

**Status:** Superseded by 009. There is no longer a separate fully-clean
profile — see 009.

## 007 — Synthetic data only

**Decision:** No real customer, order, or payment data is used anywhere in
this repository, at any phase.

**Rationale:** This is a personal learning project; using real data would
create unnecessary privacy and compliance risk for no learning benefit.

**Status:** Accepted.

## 008 — Core implementation completed manually for learning

**Decision:** AI assistance is used for scaffolding, fixtures, repetitive
configuration, tests, and documentation. Core learning-ticket implementation
(ingestion logic, transformation SQL, cloud resource configuration) is
attempted by the user first.

**Rationale:** The purpose of this project is for the user to build these
skills personally. See [LEARNING_PLAN.md](LEARNING_PLAN.md) and
[AGENTS.md](AGENTS.md) for how this is enforced.

**Status:** Accepted.

## 009 — Raw source data is dirty by default; no separate clean profile

**Decision:** Drop the separate `clean` profile (see 006). Source data now
ships as two profiles by scale — `development` (10K/100K/130K rows) and
`portfolio` (100K/1M/1.3M rows) — and **both** are realistically dirty:
most rows are valid, but a low, configurable, deterministic rate (0.1%–2%
per rule) of rows carry data-quality problems. Every column in the raw
Parquet files is typed as a string so invalid values can be preserved
rather than rejected at write time; Silver is responsible for
`TRY_CAST`/`TRY_TO_*`-style casting and cleaning.

**Rationale:** A real source-system feed is never fully clean, and giving
learners a pristine "clean" profile as an option encouraged building Silver
logic against the easy dataset instead of the realistic one. Making
dirtiness the default (rather than a separate opt-in profile) forces the
future Silver ticket to actually handle validation, casting, and
quarantine. The `portfolio` profile additionally exists to exercise
multi-file, cloud-scale ingestion patterns (e.g. Snowflake `COPY INTO`)
that the original small `development`-only design couldn't demonstrate.

**Status:** Accepted.
