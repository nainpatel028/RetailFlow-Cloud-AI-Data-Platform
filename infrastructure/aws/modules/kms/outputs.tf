output "key_arn" {
  description = "ARN of the customer-managed KMS key, or null when disabled (SSE-S3/AES256 is used instead)."
  value       = var.enabled ? aws_kms_key.data_lake[0].arn : null
}

output "key_id" {
  description = "ID of the customer-managed KMS key, or null when disabled."
  value       = var.enabled ? aws_kms_key.data_lake[0].key_id : null
}

output "alias_name" {
  description = "Alias of the customer-managed KMS key, or null when disabled."
  value       = var.enabled ? aws_kms_alias.data_lake[0].name : null
}
