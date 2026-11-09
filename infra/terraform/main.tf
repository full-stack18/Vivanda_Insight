terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-2"
}

resource "aws_s3_bucket" "vivanda_lake" {
  bucket        = "vivanda-dw-undc-2026-0864"
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "vivanda_lake" {
  bucket = aws_s3_bucket.vivanda_lake.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}