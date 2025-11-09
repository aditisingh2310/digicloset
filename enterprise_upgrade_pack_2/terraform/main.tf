terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  cluster_name    = "digicloset-cluster"
  cluster_version = "1.29"
  vpc_id          = "vpc-xxxx"
  subnet_ids      = ["subnet-xxx1","subnet-xxx2"]
}
