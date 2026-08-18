# Partial backend configuration on purpose: no bucket/key/region/account
# values are hardcoded here. Supply them at init time from the untracked
# backend.hcl (copied from backend.hcl.example), e.g.:
#
#   terraform init -backend-config=backend.hcl
#
# The state bucket comes from the bootstrap stack's `state_bucket_name`
# output (../../bootstrap).
terraform {
  backend "s3" {}
}
