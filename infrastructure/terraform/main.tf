# Main Terraform Configuration for Smart Logistics ML Infrastructure
# Provisions S3 buckets and IAM roles in LocalStack for local development

# ============================================
# S3 Bucket for ML Artifacts
# ============================================
resource "aws_s3_bucket" "ml_artifacts" {
  bucket = "smart-logistics-artifacts"

  tags = {
    Name        = "Smart Logistics ML Artifacts"
    Environment = "development"
    Project     = "smart-logistics-supply-chain-ml"
    ManagedBy   = "terraform"
  }
}

# S3 Bucket for MLflow artifacts (used by MLflow server)
resource "aws_s3_bucket" "mlflow_artifacts" {
  bucket = "ml-artifacts"

  tags = {
    Name        = "MLflow Artifacts"
    Environment = "development"
    Project     = "smart-logistics-supply-chain-ml"
    ManagedBy   = "terraform"
  }
}

# Enable versioning for the artifacts bucket
resource "aws_s3_bucket_versioning" "ml_artifacts_versioning" {
  bucket = aws_s3_bucket.ml_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================
# IAM Role for MLflow S3 Access
# ============================================
resource "aws_iam_role" "mlflow_s3_access_role" {
  name        = "mlflow-s3-access-role"
  description = "IAM role for MLflow to access S3 buckets"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "MLflow S3 Access Role"
    Environment = "development"
    Project     = "smart-logistics-supply-chain-ml"
    ManagedBy   = "terraform"
  }
}

# IAM Policy for S3 access
resource "aws_iam_role_policy" "mlflow_s3_policy" {
  name = "mlflow-s3-access-policy"
  role = aws_iam_role.mlflow_s3_access_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.ml_artifacts.arn,
          "${aws_s3_bucket.ml_artifacts.arn}/*",
          aws_s3_bucket.mlflow_artifacts.arn,
          "${aws_s3_bucket.mlflow_artifacts.arn}/*"
        ]
      }
    ]
  })
}

# ============================================
# Outputs
# ============================================
output "ml_artifacts_bucket_name" {
  description = "Name of the ML artifacts S3 bucket"
  value       = aws_s3_bucket.ml_artifacts.id
}

output "mlflow_artifacts_bucket_name" {
  description = "Name of the MLflow artifacts S3 bucket"
  value       = aws_s3_bucket.mlflow_artifacts.id
}

output "mlflow_s3_role_arn" {
  description = "ARN of the MLflow S3 access IAM role"
  value       = aws_iam_role.mlflow_s3_access_role.arn
}
