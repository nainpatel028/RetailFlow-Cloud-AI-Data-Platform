# Least-privilege role for the RetailFlow data pipeline: can list the
# project's data buckets and read/write objects in landing/bronze/silver/
# gold only (never the logs bucket, never any unrelated bucket), plus KMS
# permissions only when a customer-managed key is actually in use. No
# administrator permissions, no access keys - this role is assumed, not
# used with static credentials.
#
# TRUST MODEL - development/bootstrap only. This role trusts a single
# human IAM principal (the one currently authenticated when Terraform
# applies, obtained dynamically - see var.trusted_principal_arn), which is
# acceptable for one developer bootstrapping infrastructure by hand but is
# NOT how a production pipeline should authenticate. Production would
# replace this trust statement with:
#   - Airflow's own workload identity (e.g. an EC2/ECS/EKS instance role
#     or IRSA, so the orchestrator assumes this role without any static
#     or human credential), or
#   - CI/CD OIDC federation (e.g. GitHub Actions' `aws-actions/configure-
#     aws-credentials` against an OIDC identity provider, so a pipeline
#     run can assume this role without a stored secret at all).
# The role name is deliberately scoped `...Dev...` to make this
# development-only trust model obvious at a glance.

data "aws_iam_policy_document" "assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [var.trusted_principal_arn]
    }
  }
}

resource "aws_iam_role" "data_pipeline" {
  name                 = "RetailFlowDevDataPipelineRole"
  assume_role_policy   = data.aws_iam_policy_document.assume_role.json
  max_session_duration = 3600

  tags = var.tags
}

locals {
  bucket_arn_list    = values(var.bucket_arns)
  bucket_object_arns = [for arn in local.bucket_arn_list : "${arn}/*"]
}

data "aws_iam_policy_document" "data_pipeline" {
  statement {
    sid       = "ListProjectDataBuckets"
    effect    = "Allow"
    actions   = ["s3:ListBucket", "s3:GetBucketLocation"]
    resources = local.bucket_arn_list
  }

  statement {
    sid    = "ReadWriteDataZoneObjects"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:GetObjectVersion",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = local.bucket_object_arns
  }

  dynamic "statement" {
    for_each = var.kms_key_arn == null ? [] : [1]
    content {
      sid    = "UseCustomerManagedKmsKey"
      effect = "Allow"
      actions = [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey",
      ]
      resources = [var.kms_key_arn]
    }
  }
}

resource "aws_iam_role_policy" "data_pipeline" {
  name   = "RetailFlowDataPipelinePolicy"
  role   = aws_iam_role.data_pipeline.id
  policy = data.aws_iam_policy_document.data_pipeline.json
}
