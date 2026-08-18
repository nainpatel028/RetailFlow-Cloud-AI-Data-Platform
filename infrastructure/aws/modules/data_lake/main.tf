# Five S3 buckets for the RetailFlow data lake: four data zones
# (landing/bronze/silver/gold) plus a logs bucket that receives S3
# server-access logs from the four data-zone buckets. The logs bucket does
# not log to itself.

locals {
  data_zones = ["landing", "bronze", "silver", "gold"]

  bucket_names = {
    for zone in local.data_zones :
    zone => lower("${var.project_name}-${var.environment}-${zone}-${var.account_id}-${var.aws_region}")
  }

  logs_bucket_name = lower("${var.project_name}-${var.environment}-logs-${var.account_id}-${var.aws_region}")

  # SSE-KMS only when a customer-managed key was actually supplied;
  # otherwise the SSE-S3/AES256 default applies, which avoids the
  # additional KMS charges a customer-managed key incurs (see modules/kms).
  sse_algorithm      = var.kms_key_arn == null ? "AES256" : "aws:kms"
  bucket_key_enabled = var.kms_key_arn != null
}

# --------------------------------------------------------------------------
# Logs bucket
# --------------------------------------------------------------------------

resource "aws_s3_bucket" "logs" {
  bucket = local.logs_bucket_name

  # force_destroy = false means Terraform refuses to destroy this bucket
  # while it still contains objects, preventing accidental deletion of log
  # history. Deliberately NOT prevent_destroy: unlike the Terraform state
  # bucket, an empty logs bucket may be intentionally removed later (e.g.
  # tearing down an unused dev environment) without editing this module.
  force_destroy = false

  tags = merge(var.tags, {
    Name     = local.logs_bucket_name
    DataZone = "logs"
  })
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  # Always SSE-S3, independent of the data-zone KMS toggle: keeping the log
  # bucket's own encryption unconditional avoids a circular dependency on
  # the optional KMS key policy (a KMS key policy would otherwise need to
  # know about the logs bucket, and vice versa).
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"
    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = var.abort_incomplete_multipart_upload_days
    }
  }

  # Logs are operational exhaust, not business data: current log objects
  # DO expire here, unlike the data-zone buckets below.
  rule {
    id     = "expire-current-log-objects"
    status = "Enabled"
    filter {}

    expiration {
      days = var.logs_current_version_expiration_days
    }
  }

  rule {
    id     = "expire-noncurrent-log-versions"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.logs_noncurrent_version_expiration_days
    }
  }
}

# The logs bucket's policy has two jobs: deny any non-TLS request, and
# allow the S3 log-delivery service to write access logs for this
# project's own data-zone buckets - and nothing else. Both must live in a
# single aws_s3_bucket_policy resource because a bucket can only have one
# bucket policy attached at a time.
#
# The ownership controls above (BucketOwnerEnforced) disable ACLs
# entirely, which also disables the legacy ACL-based grant to the
# "Log Delivery" group that server access logging used historically. With
# ACLs disabled, a bucket POLICY statement granting the
# `logging.s3.amazonaws.com` service principal is the only way log
# delivery can actually succeed - without it, `aws_s3_bucket_logging`
# below would enable logging on the source buckets but every delivery
# would silently fail with AccessDenied.
data "aws_iam_policy_document" "logs_bucket_policy" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:*"]
    resources = [aws_s3_bucket.logs.arn, "${aws_s3_bucket.logs.arn}/*"]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }

  dynamic "statement" {
    for_each = local.bucket_names
    content {
      sid    = "AllowS3LogDelivery-${statement.key}"
      effect = "Allow"

      principals {
        type        = "Service"
        identifiers = ["logging.s3.amazonaws.com"]
      }

      # Restricted to this zone's own prefix in the logs bucket, matching
      # the target_prefix used by aws_s3_bucket_logging.data_zone below -
      # the landing zone's log delivery cannot write into bronze/'s
      # prefix, etc.
      actions   = ["s3:PutObject"]
      resources = ["${aws_s3_bucket.logs.arn}/${statement.key}/*"]

      # Restrict delivery to this account and to the specific source
      # bucket performing the delivery, per AWS's documented pattern for
      # server access logging to a BucketOwnerEnforced target.
      condition {
        test     = "StringEquals"
        variable = "aws:SourceAccount"
        values   = [var.account_id]
      }

      condition {
        test     = "ArnLike"
        variable = "aws:SourceArn"
        values   = [aws_s3_bucket.data_zone[statement.key].arn]
      }
    }
  }
}

resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.logs.id
  policy = data.aws_iam_policy_document.logs_bucket_policy.json
}

# --------------------------------------------------------------------------
# Data-zone buckets: landing, bronze, silver, gold
# --------------------------------------------------------------------------

resource "aws_s3_bucket" "data_zone" {
  for_each = local.bucket_names

  bucket = each.value

  # force_destroy = false means Terraform refuses to destroy a bucket that
  # still contains objects, so nonempty landing/bronze/silver/gold data
  # can never be destroyed by accident. Deliberately NOT prevent_destroy:
  # unlike the Terraform state bucket, an empty development data-zone
  # bucket may be intentionally removed later without editing this
  # module. Current objects are additionally protected from automatic
  # expiration by the lifecycle configuration below (no `expiration`
  # rule exists for current versions).
  force_destroy = false

  tags = merge(var.tags, {
    Name     = each.value
    DataZone = each.key
  })
}

resource "aws_s3_bucket_public_access_block" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_versioning" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = local.sse_algorithm
      kms_master_key_id = var.kms_key_arn
    }
    bucket_key_enabled = local.bucket_key_enabled
  }
}

# Current objects are NEVER expired automatically here - only noncurrent
# (superseded) versions and incomplete multipart uploads are cleaned up.
resource "aws_s3_bucket_lifecycle_configuration" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"
    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = var.abort_incomplete_multipart_upload_days
    }
  }

  rule {
    id     = "expire-noncurrent-versions"
    status = "Enabled"
    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.data_zone_noncurrent_version_expiration_days
    }
  }
}

resource "aws_s3_bucket_logging" "data_zone" {
  for_each = aws_s3_bucket.data_zone

  bucket        = each.value.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "${each.key}/"

  # Log delivery will fail with AccessDenied at apply time unless the
  # logs bucket's policy (granting logging.s3.amazonaws.com) exists first.
  depends_on = [aws_s3_bucket_policy.logs]
}

data "aws_iam_policy_document" "data_zone_tls_only" {
  for_each = aws_s3_bucket.data_zone

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"

    principals {
      type        = "AWS"
      identifiers = ["*"]
    }

    actions   = ["s3:*"]
    resources = [each.value.arn, "${each.value.arn}/*"]

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "data_zone_tls_only" {
  for_each = aws_s3_bucket.data_zone

  bucket = each.value.id
  policy = data.aws_iam_policy_document.data_zone_tls_only[each.key].json
}
