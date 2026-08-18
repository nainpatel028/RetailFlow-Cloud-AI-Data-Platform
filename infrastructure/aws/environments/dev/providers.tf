# Authentication is external, via AWS_PROFILE=retailflow-dev (temporary
# browser-based `aws login` credentials). No `profile` attribute is set
# here on purpose - the provider always reads whatever is currently
# authenticated in the environment, so this file never needs local
# per-machine details.
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner
    }
  }
}
