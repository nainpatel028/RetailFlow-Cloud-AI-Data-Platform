# Azure Infrastructure

**Status: NOT IMPLEMENTED.**

## Future purpose

Will hold infrastructure-as-code (e.g., Bicep or Terraform) for the Azure
resources the platform needs (storage, compute, SQL) if/when RF-006/RF-007
begin. This is now an **optional, later portability and comparison
exercise** — AWS (RF-011) is the primary cloud implementation — see
[DECISIONS.md](../../DECISIONS.md) #010 and
[docs/cloud_mapping.md](../../docs/cloud_mapping.md).

## Learning objectives

- Defining cloud resources as versioned code rather than clicking through a
  portal
- Scoping resource permissions minimally (least privilege) for a learning
  project
- Keeping all resource configuration free of embedded secrets, using
  environment-based auth instead
- Comparing Azure resource models against the AWS implementation already
  built

No resource definitions, deployment instructions, or credentials are
provided here — none exist yet.
