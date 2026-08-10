# Power BI Scope (Planned)

**Status: NOT IMPLEMENTED.** No `.pbix` file, dataset, or dashboard exists
yet. This document records the intended scope for when Power BI work
begins (RF-008).

## Intended dashboard pages

Mapped directly to the business questions in
[business_requirements.md](business_requirements.md):

1. **Revenue overview** — daily revenue trend, filterable by date range and
   sales channel.
2. **Order status** — completed vs. cancelled vs. pending order counts and
   rates, by channel and over time.
3. **Payment health** — payment-failure rate and breakdown by
   `failure_reason` and `payment_method`.
4. **Top customers** — customers ranked by total completed order value.
5. **Data reliability** — count and rate of data-quality issues detected by
   the audit layer per ingestion run (depends on RF-005).

## Intended data source

Power BI will connect to the Gold layer (planned) once it exists — not
directly to the raw Parquet source files or Bronze layer. This keeps
presentation logic out of the dashboard and in tested, versioned
transformation code.

## Learning objectives

- Building a Power BI data model from a star-schema-shaped Gold layer
- DAX measures for rate/ratio calculations (failure rate, cancellation rate)
- Basic report design for operational (not executive-glossy) dashboards
