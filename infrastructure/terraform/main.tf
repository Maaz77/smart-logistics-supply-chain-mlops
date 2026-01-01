# Main Terraform Configuration for Smart Logistics ML Infrastructure
# Provisions S3 buckets and IAM roles in LocalStack for local development
#
# IMPORTANT: This configuration is designed for LocalStack ONLY.
# All AWS resources are simulated locally - no real AWS services are used.
# Use with tflocal: cd infrastructure/terraform && tflocal apply
#
# S3 Bucket Design:
# - smart-logistics-data:     For raw/processed data, synced with ./data folder
# - mlflow-model-registry:    For MLflow artifacts, synced with ./models folder

# ============================================
# Variables
# ============================================
variable "localstack_endpoint" {
  description = "LocalStack endpoint URL for AWS CLI commands"
  type        = string
  default     = "http://localhost:4566"
}

# ============================================
# S3 Bucket for Data Storage
# ============================================
resource "aws_s3_bucket" "smart_logistics_data" {
  bucket        = "smart-logistics-data"
  force_destroy = true

  tags = {
    Name        = "Smart Logistics Data"
    Environment = "development"
    Project     = "smart-logistics-supply-chain-ml"
    ManagedBy   = "terraform"
    SyncFolder  = "./data"
  }
}

# Enable versioning for the data bucket
resource "aws_s3_bucket_versioning" "smart_logistics_data_versioning" {
  bucket = aws_s3_bucket.smart_logistics_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Sync local data folder to S3 after bucket creation (LocalStack only)
resource "null_resource" "sync_data_to_s3" {
  depends_on = [aws_s3_bucket.smart_logistics_data]

  triggers = {
    bucket_id = aws_s3_bucket.smart_logistics_data.id
  }

  provisioner "local-exec" {
    command     = <<-EOT
      echo "📤 Syncing ./data to s3://smart-logistics-data (LocalStack)..."
      # Try awslocal first (LocalStack CLI), fallback to aws with endpoint
      if command -v awslocal &> /dev/null; then
        awslocal s3 sync ../../data s3://smart-logistics-data \
          --exclude ".gitkeep" --exclude ".DS_Store" --exclude "*.tmp" 2>/dev/null || true
      else
        aws --endpoint-url=${var.localstack_endpoint} s3 sync ../../data s3://smart-logistics-data \
          --exclude ".gitkeep" --exclude ".DS_Store" --exclude "*.tmp" 2>/dev/null || true
      fi
      echo "✅ Data sync complete"
    EOT
    working_dir = path.module
  }
}

# ============================================
# S3 Bucket for MLflow Model Registry
# ============================================
resource "aws_s3_bucket" "mlflow_model_registry" {
  bucket        = "mlflow-model-registry"
  force_destroy = true

  tags = {
    Name        = "MLflow Model Registry"
    Environment = "development"
    Project     = "smart-logistics-supply-chain-ml"
    ManagedBy   = "terraform"
    SyncFolder  = "./models"
  }
}

# Enable versioning for the model registry bucket
resource "aws_s3_bucket_versioning" "mlflow_model_registry_versioning" {
  bucket = aws_s3_bucket.mlflow_model_registry.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Sync local models folder to S3 after bucket creation (LocalStack only)
resource "null_resource" "sync_models_to_s3" {
  depends_on = [aws_s3_bucket.mlflow_model_registry]

  triggers = {
    bucket_id = aws_s3_bucket.mlflow_model_registry.id
  }

  provisioner "local-exec" {
    command     = <<-EOT
      echo "📤 Syncing ./models to s3://mlflow-model-registry (LocalStack)..."
      # Try awslocal first (LocalStack CLI), fallback to aws with endpoint
      if command -v awslocal &> /dev/null; then
        awslocal s3 sync ../../models s3://mlflow-model-registry \
          --exclude ".gitkeep" --exclude ".DS_Store" --exclude "*.tmp" 2>/dev/null || true
      else
        aws --endpoint-url=${var.localstack_endpoint} s3 sync ../../models s3://mlflow-model-registry \
          --exclude ".gitkeep" --exclude ".DS_Store" --exclude "*.tmp" 2>/dev/null || true
      fi
      echo "✅ Models sync complete"
    EOT
    working_dir = path.module
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
          aws_s3_bucket.smart_logistics_data.arn,
          "${aws_s3_bucket.smart_logistics_data.arn}/*",
          aws_s3_bucket.mlflow_model_registry.arn,
          "${aws_s3_bucket.mlflow_model_registry.arn}/*"
        ]
      }
    ]
  })
}

# ============================================
# Outputs
# ============================================
output "localstack_endpoint" {
  description = "LocalStack endpoint URL"
  value       = var.localstack_endpoint
}

output "data_bucket_name" {
  description = "Name of the smart-logistics-data S3 bucket"
  value       = aws_s3_bucket.smart_logistics_data.id
}

output "data_bucket_arn" {
  description = "ARN of the smart-logistics-data S3 bucket"
  value       = aws_s3_bucket.smart_logistics_data.arn
}

output "model_registry_bucket_name" {
  description = "Name of the MLflow model registry S3 bucket"
  value       = aws_s3_bucket.mlflow_model_registry.id
}

output "model_registry_bucket_arn" {
  description = "ARN of the MLflow model registry S3 bucket"
  value       = aws_s3_bucket.mlflow_model_registry.arn
}

output "mlflow_s3_role_arn" {
  description = "ARN of the MLflow S3 access IAM role"
  value       = aws_iam_role.mlflow_s3_access_role.arn
}
