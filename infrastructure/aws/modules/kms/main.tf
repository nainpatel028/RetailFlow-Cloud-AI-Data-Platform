# Optional customer-managed symmetric KMS key for S3 SSE-KMS. Disabled by
# default (var.enabled = false): the data_lake module falls back to the
# SSE-S3/AES256 default whenever this module creates nothing, which avoids
# the additional per-key and per-request KMS charges a customer-managed
# key incurs. Only enable with explicit approval.

resource "aws_kms_key" "data_lake" {
  count = var.enabled ? 1 : 0

  description = "Customer-managed key for RetailFlow ${var.environment} data-lake S3 encryption."

  # Explicit rather than relying on the provider default, so the key's
  # type is auditable directly from this file.
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"

  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-data-lake"
  })
}

resource "aws_kms_alias" "data_lake" {
  count = var.enabled ? 1 : 0

  name          = "alias/${var.project_name}-${var.environment}-data-lake"
  target_key_id = aws_kms_key.data_lake[0].key_id
}
