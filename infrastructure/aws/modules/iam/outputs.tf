output "role_name" {
  description = "Name of the RetailFlow data-pipeline IAM role."
  value       = aws_iam_role.data_pipeline.name
}

output "role_arn" {
  description = "ARN of the RetailFlow data-pipeline IAM role. Marked sensitive because it embeds the AWS account ID."
  value       = aws_iam_role.data_pipeline.arn
  sensitive   = true
}
