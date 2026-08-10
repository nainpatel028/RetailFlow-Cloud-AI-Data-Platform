# RF-002 — Build Local Bronze Ingestion

**Status:** Next

## Business problem

Before any transformation, quality auditing, or dashboarding can happen,
the synthetic raw source Parquet files need to land in a queryable local
store (Bronze) in a way that is safe to rerun and easy to audit — without
losing or altering any of the deliberately dirty raw values.

## Scope

**This ticket is not implemented yet.** Per [AGENTS.md](../../AGENTS.md) and
[LEARNING_PLAN.md](../../LEARNING_PLAN.md), the user attempts this
implementation manually; it is not scaffolded or solved by AI ahead of that
attempt. This document defines the acceptance criteria only.

The implementation will read the `development` Parquet profile from
`data/incoming/development/<dataset>/*.parquet` (see
[docs/data_contracts.md](../data_contracts.md) for the exact raw schema —
every column is `string`) and load it into a local Bronze store, using a
local SQL database (choice of engine is part of the exercise). Bronze must
preserve every raw value exactly, including the intentionally invalid ones
(bad amounts, malformed dates, orphaned foreign keys, etc.) — do not cast,
validate, or filter anything at this stage. That belongs to Silver.

## Acceptance criteria

- [ ] Reads the `development` Parquet profile from
      `data/incoming/development/`, across all part files per dataset
- [ ] Validates that each source dataset's columns exactly match the
      contract in `docs/data_contracts.md` before loading (fails loudly if
      not)
- [ ] Loads each table into Bronze without casting, standardizing,
      repairing, deduplicating, rejecting, or quarantining any row — Bronze
      is a raw, traceable copy, including rows with invalid values
- [ ] Records an audit result for each run: source files read, row count
      read, row count loaded, timestamp of the run, and any validation
      failures
- [ ] Reconciles and reports source row count vs. destination row count for
      each table, per run (should match the `manifest.json` row counts)
- [ ] Rerunning ingestion against the same source data does not create
      duplicate rows in Bronze (idempotent load)
- [ ] Has tests covering: schema validation failure, successful load and
      count reconciliation, and idempotent rerun behavior
- [ ] No credentials are committed to Git — local DB connection details, if
      any, come from `.env` (untracked), following the placeholders in
      `.env.example`

## Out of scope for this ticket

Silver validation/casting/standardization/deduplication/quarantine, Gold
modeling, data-quality rule execution beyond basic schema-shape validation,
the `portfolio` profile, and any cloud or orchestration component.

## Dependencies

- RF-001 (data model definition) — must be in Review or Done
- Synthetic data generator (`scripts/generate_data.py`) — must be run first
  to produce `data/incoming/development/`
