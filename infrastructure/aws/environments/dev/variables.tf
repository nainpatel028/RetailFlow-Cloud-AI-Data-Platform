variable "aws_region" {
  description = "AWS region for all dev-environment resources."
  type        = string
  default     = "ca-central-1"
}

variable "project_name" {
  description = "Short project name used in resource naming and tags."
  type        = string
  default     = "retailflow"
}

variable "environment" {
  description = "Environment name used in resource naming and tags."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owning team, applied as a tag."
  type        = string
  default     = "DataEngineering"
}

variable "enable_customer_managed_kms" {
  description = "Whether to create a customer-managed KMS key for S3 encryption. Defaults to false: buckets use SSE-S3 (AES256) instead, avoiding the additional per-key and per-request KMS charges. Only enable with explicit approval, e.g. for a production demonstration."
  type        = bool
  default     = false
}

# --------------------------------------------------------------------------
# Retention (see modules/data_lake/variables.tf for full descriptions).
# Current landing/bronze/silver/gold data is never expired automatically.
# --------------------------------------------------------------------------

variable "data_zone_noncurrent_version_expiration_days" {
  description = "Days after which a noncurrent version of a landing/bronze/silver/gold object expires."
  type        = number
  default     = 90

  validation {
    condition     = var.data_zone_noncurrent_version_expiration_days > 0
    error_message = "data_zone_noncurrent_version_expiration_days must be a positive number of days."
  }
}

variable "logs_current_version_expiration_days" {
  description = "Days after which a current server-access-log object expires."
  type        = number
  default     = 90

  validation {
    condition     = var.logs_current_version_expiration_days > 0
    error_message = "logs_current_version_expiration_days must be a positive number of days."
  }
}

variable "logs_noncurrent_version_expiration_days" {
  description = "Days after which a noncurrent version of a server-access-log object expires."
  type        = number
  default     = 30

  validation {
    condition     = var.logs_noncurrent_version_expiration_days > 0
    error_message = "logs_noncurrent_version_expiration_days must be a positive number of days."
  }
}

variable "abort_incomplete_multipart_upload_days" {
  description = "Days after which incomplete multipart uploads are aborted, across every bucket in this environment."
  type        = number
  default     = 7

  validation {
    condition     = var.abort_incomplete_multipart_upload_days > 0
    error_message = "abort_incomplete_multipart_upload_days must be a positive number of days."
  }
}
