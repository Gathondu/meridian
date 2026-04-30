provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region used by the default provider."
  default     = "eu-central-1"
}
