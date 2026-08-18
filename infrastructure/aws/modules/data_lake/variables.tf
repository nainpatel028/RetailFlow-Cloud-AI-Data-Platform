variable "project_name" {
  description = "Short project name used in bucket naming and tags."
  type        = string
}

variable "environment" {
  description = "Environment name (e.g. dev, prod) used in bucket naming and tags."
  type        = string
}

variable "aws_region" {
  description = "AWS region the buckets are created in, used for bucket naming."
  type        = string
}

variable "account_id" {
  description = "AWS account ID, used only to guarantee globally-unique bucket names. Always sourced dynamically by the caller via data.aws_caller_identity - never hardcode this."
  type        = string
}

variable "kms_key_arn" {
  description = "ARN of a customer-managed KMS key to use for SSE-KMS on the data-zone buckets. Null (the default) means SSE-S3/AES256 is used instead - see modules/kms."
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags merged onto every resource this module creates."
  type        = map(string)
  default     = {}
}

# --------------------------------------------------------------------------
# Retention (all configurable; current landing/bronze/silver/gold data is
# never deleted automatically - only noncurrent versions and logs expire).
# --------------------------------------------------------------------------

variable "data_zone_noncurrent_version_expiration_days" {
  description = "Days after which a noncurrent (superseded) version of a landing/bronze/silver/gold object expires. Current objects are never expired automatically - this only cleans up old versions left behind by versioning."
  type        = number
  default     = 90

  validation {
    condition     = var.data_zone_noncurrent_version_expiration_days > 0
    error_message = "data_zone_noncurrent_version_expiration_days must be a positive number of days."
  }
}

variable "logs_current_version_expiration_days" {
  description = "Days after which a current server-access-log object expires. Logs are operational exhaust, not business data, so (unlike the data zones) current log objects do expire."
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
  description = "Days after which incomplete multipart uploads are aborted, across every bucket this module creates."
  type        = number
  default     = 7

  validation {
    condition     = var.abort_incomplete_multipart_upload_days > 0
    error_message = "abort_incomplete_multipart_upload_days must be a positive number of days."
  }
}
