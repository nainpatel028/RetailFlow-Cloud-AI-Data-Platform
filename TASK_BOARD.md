# Task Board

Simple Kanban-style tracking for RetailFlow tickets. Update this file as
ticket status changes; do not delete completed rows — move them to Done.

## Review

- **RF-001** — Define MVP data model (three-table grain, keys, relationships)

## Next

- **RF-002** — Build local Bronze ingestion (manual implementation, see
  [docs/tickets/RF-002_build_local_bronze_ingestion.md](docs/tickets/RF-002_build_local_bronze_ingestion.md))

## Backlog

- RF-003 — Silver transformation and cleansing rules
- RF-004 — Gold aggregation layer answering the business questions
- RF-005 — Data-quality audit engine against the dirty `development`/`portfolio` source profiles
- RF-006 — Azure storage + compute implementation
- RF-007 — Azure SQL / warehouse implementation
- RF-008 — Power BI dashboard build
- RF-009 — n8n read-only operations agent (observe + report only)
- RF-010 — n8n human-approval action flow
- RF-011 — AWS port of Azure implementation
- RF-012 — CI/CD pipeline
- RF-013 — Monitoring and alerting

## In Progress

*(none)*

## Done

*(none yet — RF-001 moves here once scaffolding is verified per
[PROJECT_CONTEXT.md](PROJECT_CONTEXT.md))*
