# Partial backend configuration on purpose: no bucket/key/region/account
# values are hardcoded here. Supply them at init time from the untracked
# backend.hcl (copied from backend.hcl.example), e.g.:
#
#   terraform init -backend-config=backend.hcl -migrate-state
#
# Chicken-and-egg: this stack creates the state bucket, so the first apply
# runs with local state. Add this backend afterwards and migrate the local
# state into the bucket it just created (see ../README.md).
terraform {
  backend "s3" {}
}
