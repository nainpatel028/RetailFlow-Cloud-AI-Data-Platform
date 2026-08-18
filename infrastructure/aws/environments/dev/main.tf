locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
  }
}

# Identifies the principal currently authenticated via AWS_PROFILE - used
# both to build globally-unique bucket names (account ID) and as the sole
# trusted principal for the pipeline role's trust policy. Never hardcoded.
data "aws_caller_identity" "current" {}

module "kms" {
  source = "../../modules/kms"

  enabled      = var.enable_customer_managed_kms
  project_name = var.project_name
  environment  = var.environment
  tags         = local.common_tags
}

module "data_lake" {
  source = "../../modules/data_lake"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  account_id   = data.aws_caller_identity.current.account_id
  kms_key_arn  = module.kms.key_arn
  tags         = local.common_tags

  data_zone_noncurrent_version_expiration_days = var.data_zone_noncurrent_version_expiration_days
  logs_current_version_expiration_days         = var.logs_current_version_expiration_days
  logs_noncurrent_version_expiration_days      = var.logs_noncurrent_version_expiration_days
  abort_incomplete_multipart_upload_days       = var.abort_incomplete_multipart_upload_days
}

module "iam" {
  source = "../../modules/iam"

  project_name          = var.project_name
  environment           = var.environment
  bucket_arns           = module.data_lake.bucket_arns
  trusted_principal_arn = data.aws_caller_identity.current.arn
  kms_key_arn           = module.kms.key_arn
  tags                  = local.common_tags
}
