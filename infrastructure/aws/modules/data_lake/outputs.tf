output "bucket_names" {
  description = "Map of data-zone name (landing/bronze/silver/gold) to S3 bucket name."
  value       = { for zone, bucket in aws_s3_bucket.data_zone : zone => bucket.id }
}

output "bucket_arns" {
  description = "Map of data-zone name (landing/bronze/silver/gold) to S3 bucket ARN."
  value       = { for zone, bucket in aws_s3_bucket.data_zone : zone => bucket.arn }
}

output "logs_bucket_name" {
  description = "Name of the server-access-logging target bucket."
  value       = aws_s3_bucket.logs.id
}

output "logs_bucket_arn" {
  description = "ARN of the server-access-logging target bucket."
  value       = aws_s3_bucket.logs.arn
}
