# Cloud Mapping (Planned)

**Status: NOT IMPLEMENTED.** This document records the intended mapping of
pipeline stages to Azure services, and the equivalent AWS services for the
later port. No cloud resources have been created. See
[DECISIONS.md](../DECISIONS.md) #003 for why Azure is built first.

## Stage-to-service mapping (planned)

| Pipeline stage         | Azure (built first)             | AWS (ported later)          |
|--------------------------|----------------------------------|-------------------------------|
| Raw file landing          | Azure Blob Storage / ADLS Gen2  | Amazon S3                     |
| Bronze/Silver/Gold compute | Azure Data Factory or Databricks/Synapse (TBD in RF-006/007) | AWS Glue or equivalent (TBD in RF-011) |
| Structured storage         | Azure SQL Database, Synapse, or Snowflake (TBD in RF-006/007) | Amazon RDS or Redshift        |
| Orchestration               | n8n (self-hosted or cloud)      | n8n (self-hosted or cloud)    |
| Dashboarding                 | Power BI                        | Power BI (unchanged, connects to either cloud) |
| Monitoring                   | Azure Monitor                   | Amazon CloudWatch             |
| Secrets                      | Azure Key Vault                 | AWS Secrets Manager           |

Exact service choices within each cell will be finalized in their
respective tickets (RF-006 onward), not in this scaffolding session. The
`portfolio` data profile (~2.4M rows across three datasets, multiple Parquet
part files per dataset) exists specifically so that a future ticket can
demonstrate cloud-scale, multi-file ingestion — for example a Snowflake
external stage plus `COPY INTO` over the `portfolio` Parquet files. No
Snowflake objects, stages, or `COPY INTO` commands exist yet; this is a
target for a later ticket, not something this scaffolding session sets up.

## Principles for the eventual implementation

- No credentials are ever committed to this repository; cloud auth uses
  local environment variables or the cloud provider's CLI login, documented
  in `.env.example` placeholders only.
- The Azure implementation is built and understood first; the AWS port is a
  deliberate comparison exercise afterward, not a parallel build.
- Cloud resources created for this project are synthetic/learning-scale —
  no production traffic, no real customer data.
