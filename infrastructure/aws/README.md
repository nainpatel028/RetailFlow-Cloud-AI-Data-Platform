# AWS Infrastructure

**Status: NOT IMPLEMENTED.**

## Future purpose

Will hold Terraform infrastructure-as-code for the primary AWS cloud
foundation — S3, IAM, and KMS as the base layer feeding Snowflake — once
RF-011 begins (see [DECISIONS.md](../../DECISIONS.md) #010). This is the
first cloud platform built for this project, not a port of an existing
Azure implementation.

## Target architecture

Terraform → AWS S3/IAM/KMS → Snowflake RAW → dbt Silver/Gold → Airflow →
Power BI + AI + monitoring

## Learning objectives

- Designing least-privilege IAM roles and policies from scratch
- Provisioning S3 storage and KMS encryption with Terraform
- Structuring Terraform for a small, real project (modules, environments,
  remote state)
- Keeping all resource configuration free of embedded secrets

No resource definitions, deployment instructions, or credentials are
provided here — none exist yet.
