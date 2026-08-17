# AWS Orchestration

**Status: NOT IMPLEMENTED.**

## Future purpose

Will hold the AWS pipeline/orchestration definitions — primarily Airflow —
for the primary cloud implementation, once RF-011 begins (see
[DECISIONS.md](../../DECISIONS.md) #010). This is the first orchestration
platform built for this project, not a port of an existing Azure
implementation.

## Learning objectives

- Building Airflow DAGs that orchestrate Snowflake/dbt runs
- Scoping least-privilege IAM for orchestration workloads
- Identifying what is genuinely provider-specific vs. portable in a data
  pipeline design, useful if the later optional Azure comparison happens

No deployment instructions or credentials are provided here — none exist
yet. See [docs/cloud_mapping.md](../../docs/cloud_mapping.md) for the
planned service mapping.
