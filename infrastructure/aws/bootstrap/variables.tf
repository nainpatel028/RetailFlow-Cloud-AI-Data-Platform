variable "aws_region" {
  description = "AWS region for the Terraform state backend."
  type        = string
  default     = "ca-central-1"
}

variable "project_name" {
  description = "Short project name used in resource naming and tags."
  type        = string
  default     = "retailflow"
}

variable "environment" {
  description = "Environment tag applied to bootstrap resources."
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owning team, applied as a tag."
  type        = string
  default     = "DataEngineering"
}

variable "state_noncurrent_version_expiration_days" {
  description = "Days after which a noncurrent (superseded) version of the Terraform state object expires. The current state version is never expired automatically - this only cleans up old versions left behind by versioning."
  type        = number
  default     = 90

  validation {
    condition     = var.state_noncurrent_version_expiration_days > 0
    error_message = "state_noncurrent_version_expiration_days must be a positive number of days."
  }
}

variable "abort_incomplete_multipart_upload_days" {
  description = "Days after which incomplete multipart uploads to the state bucket are aborted."
  type        = number
  default     = 7

  validation {
    condition     = var.abort_incomplete_multipart_upload_days > 0
    error_message = "abort_incomplete_multipart_upload_days must be a positive number of days."
  }
}
