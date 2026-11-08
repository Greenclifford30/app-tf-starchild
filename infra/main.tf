terraform {
  required_version = ">= 1.5.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Environment = var.environment
    })
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  # Keep the storefront's production origins even when deployment-specific
  # tfvars supply additional Amplify or local development origins.
  cors_allowed_origins = distinct(concat(var.allowed_origins, [
    "https://starchildclo.com",
    "https://www.starchildclo.com"
  ]))
}
