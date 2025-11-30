# Minimal Terraform skeleton for cloud infra (placeholder)
terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "static_assets" {
  bucket = var.static_bucket_name
  acl    = "private"
}

output "static_bucket" {
  value = aws_s3_bucket.static_assets.id
}
