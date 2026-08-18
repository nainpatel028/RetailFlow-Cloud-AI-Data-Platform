# AWS Infrastructure

**Status: CODE WRITTEN, NOT APPLIED.** No AWS resources exist yet — see
[What's NOT implemented yet](#whats-not-implemented-yet) for exactly what
has and hasn't been run against this code so far.

## Architecture and purpose

This is the primary cloud implementation for RetailFlow (RF-011 — see
[DECISIONS.md](../../DECISIONS.md) #010). It provisions the foundational
layer that later tickets build on:

```text
Terraform → AWS S3/IAM/KMS → Snowflake RAW → dbt Silver/Gold → Airflow →
Power BI + AI + monitoring
```

This ticket covers only the leftmost step: an S3-based data lake (landing,
bronze, silver, gold, logs), a least-privilege IAM role for the future
pipeline, and an optional KMS key. Snowflake, dbt, Airflow, and everything
downstream are separate, later tickets.

## Two-stage workflow: bootstrap, then environment

Terraform state needs somewhere to live before anything else can use a
remote backend — the classic chicken-and-egg problem. This is solved with
two independent stacks:

1. **`bootstrap/`** — creates one S3 bucket to hold Terraform remote state.
   Uses **local** state itself (there's nothing else to point it at yet).
   Apply this once per AWS account/region.
2. **`environments/dev/`** — the actual data-lake infrastructure (via
   `modules/data_lake`, `modules/kms`, `modules/iam`). Uses the bucket
   `bootstrap` created as its **remote** S3 backend, configured via a
   partial backend block (`backend.tf`) filled in at `init` time from an
   untracked `backend.hcl` (copy `backend.hcl.example` and fill in the
   bucket name from `bootstrap`'s output).

```text
infrastructure/aws/
├── bootstrap/        # one-time per account/region: the state bucket, local state
├── modules/
│   ├── data_lake/     # 5 S3 buckets: landing, bronze, silver, gold, logs
│   ├── kms/            # optional customer-managed key (disabled by default)
│   └── iam/             # RetailFlowDevDataPipelineRole
└── environments/
    └── dev/            # wires the modules together, remote (S3) state
```

## Local authentication

Authentication is external to Terraform — never configured inside a
provider block, and never a static access key. Use temporary,
browser-based credentials:

```bash
aws login --profile retailflow-dev
export AWS_PROFILE=retailflow-dev
```

Terraform and the AWS CLI both pick up `AWS_PROFILE` from the environment.
No `profile` attribute appears anywhere in this codebase's `.tf` files —
that would tie the configuration to one person's machine.

**Production would not use this pattern at all.** A real production
environment would authenticate via **AWS IAM Identity Center** (SSO) for
human operators, or **CI/CD OIDC federation** (e.g. GitHub Actions'
`aws-actions/configure-aws-credentials` with an OIDC provider, no stored
secret at all) for automated pipelines — not a long-lived IAM user in
either case. This project uses a temporary browser-based login because
it's a single-developer learning environment, not because it's the
recommended production pattern.

## Cost — read this before applying anything

**No guarantee of "free" or "no cost" is made anywhere in this codebase or
this document.** This account currently uses the **AWS Free Plan**. That
gives a limited set of monthly credits/allowances, not a blanket
exemption from billing:

- S3 **storage**, **requests** (PUT/GET/LIST), **versioning** (every
  version of every object counts toward storage), and **server-access
  logs** (themselves stored objects, also versioned) all consume Free
  Plan credits/allowances. Once an allowance is exhausted, or if usage
  moves outside what the Free Plan covers, normal charges apply.
- **Customer-managed KMS is disabled by default**
  (`enable_customer_managed_kms = false` in
  `environments/dev/variables.tf`) specifically because it can incur
  additional charges (a per-key charge plus per-request charges) that
  fall outside typical Free Plan coverage — only set this to `true` with
  explicit approval.
- **Usage must be monitored.** Check the AWS Billing console / Cost
  Explorer periodically after applying anything in this codebase — this
  repository has no automated cost monitoring or budget alarm configured
  (that would be a separate, later ticket).
- **AWS Organizations is intentionally not used for this account.**
  Enabling Organizations changes the account's billing relationship and
  would expire this account's Free Plan credits — so this project avoids
  it on purpose, not as an oversight.
- **No permanent access keys are created anywhere in this code.** The IAM
  role is assumed via STS, not used with static credentials — this is a
  security control, not a cost control, but it's listed here because
  static keys are a common source of *unexpected* cost (e.g. a leaked key
  used for cryptomining) as well as a security risk.
- **`force_destroy = false`** on every bucket (state, logs, and all four
  data zones) — Terraform refuses to destroy any bucket that still
  contains objects, so nonempty data can never be destroyed by accident.
  This protects against accidental data loss; it does not protect against
  accidental cost.
- **`prevent_destroy = true`** on the **Terraform state bucket only** —
  state is irreplaceable, so it can never be destroyed at all, empty or
  not. The four data-zone buckets and the logs bucket deliberately do
  **not** carry `prevent_destroy`, so an empty, no-longer-needed dev
  bucket (e.g. tearing down an unused environment) can still be removed
  intentionally later, rather than accumulating storage cost forever.
  `force_destroy = false` still blocks destroying any of them while they
  hold data.

See [Retention](#retention) below for how long objects are actually kept
(and therefore billed for storage).

## Retention

Retention is configurable (see each module's `variables.tf`) and defaults
to:

| Data | Retention |
|---|---|
| Landing/Bronze/Silver/Gold — current objects | **Never expires automatically** |
| Landing/Bronze/Silver/Gold — noncurrent (superseded) versions | 90 days |
| Logs bucket — current objects | 90 days |
| Logs bucket — noncurrent versions | 30 days |
| Terraform state — current version | **Never expires automatically** |
| Terraform state — noncurrent versions | 90 days |
| Incomplete multipart uploads (every bucket) | Aborted after 7 days |

Current business data (landing/bronze/silver/gold) and the current
Terraform state version are never subject to automatic deletion in this
codebase — only old, superseded versions and operational log exhaust
expire, and only after the windows above.

## Security controls implemented

- S3 Block Public Access: all four controls enabled on every bucket.
- S3 Object Ownership: `BucketOwnerEnforced` on every bucket (disables
  ACLs entirely).
- Versioning enabled on every bucket.
- Default encryption on every bucket (SSE-S3/AES256, or SSE-KMS with S3
  Bucket Keys when the optional KMS key is enabled).
- TLS-only bucket policy (denies any request where
  `aws:SecureTransport` is `false`) on every bucket.
- Server-access logging from the four data-zone buckets to the dedicated
  `logs` bucket (the `logs` bucket does not log to itself). Because
  `BucketOwnerEnforced` disables ACLs, the legacy ACL-based grant to S3's
  "Log Delivery" group cannot work — the `logs` bucket instead carries an
  explicit policy statement granting the `logging.s3.amazonaws.com`
  service principal `s3:PutObject`, scoped to each source bucket's own
  prefix and restricted by `aws:SourceAccount`/`aws:SourceArn`
  conditions. `aws_s3_bucket_logging` on each data-zone bucket explicitly
  `depends_on` that policy so delivery permissions exist before logging
  is enabled.
- Least-privilege `RetailFlowDevDataPipelineRole` (name deliberately
  includes `Dev` — see [IAM trust model](#iam-trust-model) below): trusts
  only the current authenticated bootstrap principal (obtained
  dynamically via `data.aws_caller_identity`, never hardcoded); can list
  the project's buckets and read/write objects only in
  landing/bronze/silver/gold (not `logs`, not any unrelated bucket); no
  administrator permissions; KMS permissions granted only when the
  optional customer-managed key exists.
- Terraform state bucket (`bootstrap/`): same public-access, ownership,
  versioning, and TLS-only controls, plus **native S3 state locking**
  (`use_lockfile = true`) — no DynamoDB lock table, since DynamoDB-based
  Terraform locking is deprecated.
- No account ID, ARN, token, or credential is ever hardcoded in tracked
  files. Uniqueness (bucket names) is derived dynamically at plan/apply
  time via `data.aws_caller_identity`.

## IAM trust model

`RetailFlowDevDataPipelineRole` currently trusts a single human IAM
principal: whoever is authenticated (via `AWS_PROFILE=retailflow-dev`)
when Terraform applies, obtained dynamically — never a hardcoded ARN. This
is acceptable for one developer bootstrapping infrastructure by hand, but
it is a development/bootstrap pattern, not a production one.

**Production would replace this trust statement**, not extend it, with
one of:

- **Airflow's own workload identity** (an EC2/ECS/EKS instance role, or
  IRSA on EKS) — so the orchestrator assumes this role without any human
  or static credential involved at all, or
- **CI/CD OIDC federation** (e.g. GitHub Actions'
  `aws-actions/configure-aws-credentials` against an OIDC identity
  provider) — so a pipeline run can assume this role without a stored
  secret.

The role's S3 permissions are already scoped correctly for either future:
`ListBucket`/`GetBucketLocation` on the four data-zone bucket ARNs, and
`GetObject`/`GetObjectVersion`/`PutObject`/`DeleteObject` on objects
within those same four buckets only — never the `logs` bucket, never any
bucket outside this project. Swapping the trust principal later doesn't
require touching the permissions policy.

## Commands

Run these from `bootstrap/` or `environments/dev/` as appropriate.

```bash
# Format all Terraform files in this codebase
terraform fmt -recursive infrastructure/aws

# Check formatting without changing anything (CI-style)
terraform fmt -check -recursive infrastructure/aws

# Initialize (downloads providers; -backend=false skips remote state,
# useful for local validation without AWS credentials)
terraform init -backend=false

# Initialize for real, wiring up the S3 backend (environments/dev only,
# after copying backend.hcl.example -> backend.hcl and filling in the
# bootstrap bucket name)
terraform init -backend-config=backend.hcl

# Validate configuration (syntax + internal consistency; no AWS calls)
terraform validate

# Plan (shows what WOULD change — requires real AWS credentials and makes
# read-only AWS API calls; does not create/modify/destroy anything)
terraform plan

# Apply — NEVER run this without explicit human review of the plan output
# first. This is the one command in this list that actually creates,
# modifies, or destroys real AWS resources.
terraform apply

# Destroy — same warning as apply, in reverse. The Terraform state bucket
# is blocked from deletion regardless (prevent_destroy = true); data-zone
# and logs buckets can be destroyed only while empty (force_destroy =
# false). This is a last-resort command either way.
terraform destroy
```

**`terraform apply` requires human review and approval before every run.**
Nothing in this repository runs `apply` automatically. Review the `plan`
output line by line first.

## What's NOT implemented yet

- No `terraform apply` has ever been run against this code — no AWS
  resource described here exists. A read-only `terraform plan` has been
  run against `bootstrap/` (confirmed 7 resources to add, 0 to
  change/destroy — the expected result against an account where nothing
  has been created yet). `environments/dev/` cannot be planned against a
  real backend until `bootstrap/` is actually applied and its state
  bucket exists — that is deliberately not done as part of this ticket.
- No Snowflake, dbt, or Airflow configuration (later tickets).
- No CI/CD pipeline for Terraform (`terraform fmt -check` /
  `terraform validate` are documented above as manual commands for now).
- No Azure comparison implementation (optional, later — see
  [DECISIONS.md](../../DECISIONS.md) #010).
