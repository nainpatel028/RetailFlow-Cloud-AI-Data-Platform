# Cloud Mapping (Planned)

**Status: NOT IMPLEMENTED.** This document records the intended mapping of
pipeline stages to AWS services (the primary cloud implementation), and the
equivalent Azure services for an optional later portability comparison. No
cloud resources have been created. See [DECISIONS.md](../DECISIONS.md) #010
for why AWS is built first.

## Stage-to-service mapping (planned)

| Pipeline stage         | AWS (built first, primary — RF-011 onward) | Azure (optional later comparison — RF-006/007) |
|--------------------------|----------------------------------|-------------------------------|
| Raw file landing          | Amazon S3                        | Azure Blob Storage / ADLS Gen2 |
| Identity & access           | AWS IAM                          | Azure AD / RBAC (TBD)          |
| Encryption                   | AWS KMS                          | Azure Key Vault keys (TBD)     |
| Structured storage / warehouse | Snowflake (RAW landing, transformed via dbt) | Azure SQL Database, Synapse, or Snowflake (TBD) |
| Transformation                | dbt (Silver/Gold models in Snowflake) | Azure Data Factory or Databricks/Synapse (TBD) |
| Orchestration                  | Airflow, plus n8n (self-hosted or cloud) | n8n (self-hosted or cloud) |
| Dashboarding                    | Power BI                         | Power BI (unchanged, connects to either cloud) |
| Monitoring                      | Amazon CloudWatch                | Azure Monitor                  |
| Secrets                         | AWS Secrets Manager              | Azure Key Vault                |

Exact service choices within each cell will be finalized in their
respective tickets (RF-011 onward), not in this scaffolding session. The
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
- The AWS implementation is built and understood first (RF-011); an Azure
  port/comparison (RF-006/007) is an optional exercise afterward, not a
  parallel build.
- Cloud resources created for this project are synthetic/learning-scale —
  no production traffic, no real customer data.
