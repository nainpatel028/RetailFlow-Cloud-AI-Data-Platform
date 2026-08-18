variable "enabled" {
  description = "Whether to create the customer-managed KMS key. This incurs an AWS charge per key per month plus request costs - defaults to false. Only enable with explicit approval, e.g. for a production demonstration."
  type        = bool
  default     = false
}

variable "project_name" {
  description = "Short project name used in the key alias."
  type        = string
}

variable "environment" {
  description = "Environment name used in the key alias."
  type        = string
}

variable "tags" {
  description = "Common tags applied to the key, when created."
  type        = map(string)
  default     = {}
}
