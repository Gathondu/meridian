# Terraform (AWS)

This directory holds infrastructure for Meridian on AWS (for example VPC, ECS/Fargate, Application Load Balancer, ECR, IAM, and observability).

## Conventions

- Keep modules small and composable as the stack grows.
- Use remote state (for example S3 backend with DynamoDB locking) before any shared or production applies.
- Do not commit secrets; use `*.tfvars` for local overrides (those patterns are gitignored at repo root where applicable, and under this folder).

## Getting started

```bash
cd infra/terraform
terraform init
terraform validate
```

Applying real resources requires AWS credentials configured for the Terraform AWS provider and additional `.tf` files defining resources.
