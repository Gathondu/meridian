terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
  bucket = "meridian-terraform-state-488255002567"
  key    = "meridian/terraform.tfstate"
  region = "eu-central-1"
}

}
