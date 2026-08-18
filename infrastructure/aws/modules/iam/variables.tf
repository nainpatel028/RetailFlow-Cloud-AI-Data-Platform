variable "project_name" {
  description = "Short project name, used for tagging."
  type        = string
}

variable "environment" {
  description = "Environment name, used for tagging."
  type        = string
}

variable "bucket_arns" {
  description = "Map of data-zone name to bucket ARN for the landing/bronze/silver/gold buckets this role may read and write. The logs bucket is intentionally excluded."
  type        = map(string)
}

variable "trusted_principal_arn" {
  description = "ARN of the sole principal allowed to assume this role - the current authenticated bootstrap principal, obtained dynamically via data.aws_caller_identity in the calling root module. Never hardcode this."
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of the customer-managed KMS key to grant encrypt/decrypt/data-key permissions for. Null (the default) grants no KMS permissions at all, matching customer-managed KMS being disabled."
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags applied to the role."
  type        = map(string)
  default     = {}
}
