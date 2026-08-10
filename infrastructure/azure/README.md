# Azure Infrastructure

**Status: NOT IMPLEMENTED.**

## Future purpose

Will hold infrastructure-as-code (e.g., Bicep or Terraform) for the Azure
resources the platform needs (storage, compute, SQL) once RF-006/RF-007
begin, per the mapping in
[docs/cloud_mapping.md](../../docs/cloud_mapping.md).

## Learning objectives

- Defining cloud resources as versioned code rather than clicking through a
  portal
- Scoping resource permissions minimally (least privilege) for a learning
  project
- Keeping all resource configuration free of embedded secrets, using
  environment-based auth instead

No resource definitions, deployment instructions, or credentials are
provided here — none exist yet.
