# Architecture

This document shows the target end-to-end architecture for the RetailFlow
platform. **Most of this is planned, not implemented.** See
[PROJECT_CONTEXT.md](../PROJECT_CONTEXT.md) for current status.

## Legend

- ✅ Implemented today
- 🕒 Planned (documentation/scaffolding only)

## Data flow (medallion architecture)

```mermaid
flowchart LR
    A["Incoming raw Parquet<br/>(dirty by design)<br/>✅ synthetic generator"] --> B["Bronze<br/>preserves raw values<br/>🕒 planned (RF-002)"]
    B --> C["Silver<br/>TRY_CAST, standardize,<br/>dedupe, quarantine<br/>🕒 planned"]
    C --> D["Gold<br/>analytics-ready models<br/>🕒 planned"]
    D --> E["Power BI<br/>🕒 planned"]

    B -.-> Q["Data-quality audit<br/>🕒 planned"]
    C -.-> Q
    Q -.-> M["Monitoring<br/>🕒 planned"]
```

## Local vs. cloud implementations

```mermaid
flowchart TB
    subgraph Local["Local (this repo, session 1)"]
        L1["Raw Parquet source files ✅<br/>(development + portfolio profiles)"]
        L2["Local SQL Bronze/Silver/Gold 🕒"]
    end

    subgraph AWSImpl["AWS cloud foundation 🕒 planned (RF-011, primary)"]
        AW1["S3 / IAM / KMS (Terraform)"]
        AW2["Snowflake RAW"]
        AW3["dbt Silver/Gold + Airflow"]
    end

    subgraph AzureImpl["Azure comparison 🕒 planned (optional, later)"]
        AZ1["Storage"]
        AZ2["Compute / pipeline"]
        AZ3["SQL / warehouse"]
    end

    Local --> AWSImpl
    AWSImpl -. "optional comparison" .-> AzureImpl
```

AWS is built first as the primary cloud implementation (RF-011); Azure is
an optional, later comparison exercise (see [DECISIONS.md](../DECISIONS.md)
#010, which supersedes #003's Azure-first sequencing). Cloud resource
mapping notes are in [cloud_mapping.md](cloud_mapping.md).

## Operations agent (n8n)

```mermaid
flowchart LR
    P["Pipeline / data-quality state<br/>🕒 planned"] --> N["n8n read-only agent<br/>🕒 planned"]
    N --> R["Reports / answers to operator"]
    N -. "proposed action" .-> H{"Human approval?"}
    H -- approved --> ACT["External action<br/>🕒 planned"]
    H -- denied --> STOP["No action taken"]
```

The agent can observe and report on pipeline/data state. It cannot take any
externally-visible action without a human approving that specific action —
see [DECISIONS.md](../DECISIONS.md) #005 and
[agentic_ai_scope.md](agentic_ai_scope.md).

## Component status summary

| Component                     | Status |
|--------------------------------|--------|
| Synthetic raw source-data generator (Parquet, development + portfolio) | ✅ Implemented |
| Bronze ingestion (preserves raw values) | 🕒 Planned (RF-002) |
| Silver transformation (cast, standardize, dedupe, quarantine) | 🕒 Planned |
| Gold aggregation                | 🕒 Planned |
| Data-quality audit              | 🕒 Planned |
| AWS cloud foundation (Terraform, primary) | 🕒 Planned (RF-011) |
| Azure comparison (optional, later) | 🕒 Planned |
| Power BI dashboards             | 🕒 Planned |
| n8n read-only operations agent  | 🕒 Planned |
| Monitoring                      | 🕒 Planned |
| CI/CD                           | 🕒 Planned |
