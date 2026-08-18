# Only the nonsensitive values needed to configure environments/dev's
# partial S3 backend (backend.hcl) are exposed here - no account ID or
# ARN output.

output "state_bucket_name" {
  description = "Name of the S3 bucket created to hold Terraform remote state. Copy into environments/dev/backend.hcl as `bucket`."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_region" {
  description = "Region of the Terraform state bucket. Copy into environments/dev/backend.hcl as `region`."
  value       = var.aws_region
}
