# Terraform (AWS)

This stack provisions:

- **ECR** — container images for the FastAPI API.
- **Lambda** — public HTTPS API from an ECR image through a Lambda Function URL with response streaming enabled.
- **S3 + CloudFront** — static SvelteKit build (SPA fallback to `index.html`).
- **S3 (private)** — chat session JSON objects (`CHAT_SESSIONS_S3_PREFIX`, default `sessions/`).
- **IAM** — Lambda execution role with CloudWatch logs, S3 chat access, and optional Secrets Manager read access.
- **Secrets Manager** — optional `OPENAI_API_KEY` when `openai_api_key` is non-empty.

Variable names mirror `TF_VAR_*` / `terraform.tfvars`; see `terraform.tfvars.example`.

## Conventions

- Keep modules small and composable as the stack grows.
- Use remote state (for example S3 backend with DynamoDB locking) before any shared or production applies.
- Do not commit secrets; `*.tfvars` is gitignored (use `terraform.tfvars.example` as a template).

## Bootstrap (first time)

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set `mcp_server_url`, OpenAI/OpenRouter values, and any optional CORS origins.
2. From this directory, run `terraform init` then create ECR first with `terraform apply -auto-approve -target=aws_ecr_repository.api`.
3. Build and push `docker/Dockerfile.backend` to the ECR repository output using the same `api_image_tag` you will apply.
4. Run `terraform apply` to create the Lambda Function URL, S3, CloudFront, IAM, and secrets.
5. For GitHub Actions, add repository secrets **`AWS_ACCESS_KEY_ID`**, **`AWS_SECRET_ACCESS_KEY`**, **`MCP_SERVER_URL`**, **`OPENAI_API_KEY`**, and optionally **`OPENAI_BASE_URL`** / **`OPENAI_MODEL`** for OpenRouter.

For OpenRouter, set `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and use an OpenRouter model id in `OPENAI_MODEL`.

## Getting started

```bash
cd infra/terraform
terraform init
terraform validate
```

Applying real resources requires AWS credentials configured for the Terraform AWS provider.
