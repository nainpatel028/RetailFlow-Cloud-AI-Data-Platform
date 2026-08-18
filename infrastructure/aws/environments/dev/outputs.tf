output "bucket_names" {
  description = "Map of data-zone name (landing/bronze/silver/gold) to S3 bucket name."
  value       = module.data_lake.bucket_names
}

output "logs_bucket_name" {
  description = "Name of the server-access-logging bucket."
  value       = module.data_lake.logs_bucket_name
}

output "data_pipeline_role_name" {
  description = "Name of the RetailFlow data-pipeline IAM role."
  value       = module.iam.role_name
}

output "data_pipeline_role_arn" {
  description = "ARN of the RetailFlow data-pipeline IAM role. Marked sensitive because it embeds the AWS account ID."
  value       = module.iam.role_arn
  sensitive   = true
}

output "customer_managed_kms_enabled" {
  description = "Whether a customer-managed KMS key was created for this environment."
  value       = var.enable_customer_managed_kms
}
