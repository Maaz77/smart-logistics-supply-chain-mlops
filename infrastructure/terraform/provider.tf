# Terraform Provider Configuration for LocalStack
# This configuration points all AWS endpoints to LocalStack for local development

terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# AWS Provider configured for LocalStack
# All endpoints point to http://localhost:4566 for host-to-container communication
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  # Enable path-style S3 URLs (required for LocalStack)
  s3_use_path_style = true

  # Configure all endpoints to use LocalStack
  endpoints {
    s3  = "http://localhost:4566"
    iam = "http://localhost:4566"
    sts = "http://localhost:4566"
    rds = "http://localhost:4566"
  }
}
