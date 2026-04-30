# Terraform (AWS)

This stack provisions:

- **ECR** — container images for the FastAPI API (same image family ECS would pull; App Runner deploys from ECR).
- **App Runner** — public HTTPS API with environment variables and secrets wired from Terraform variables (aligned with `backend/.env.example`).
- **S3 + CloudFront** — static SvelteKit build (SPA fallback to `index.html`).
- **S3 (private)** — chat session JSON objects (`CHAT_SESSIONS_S3_PREFIX`, default `sessions/`).
- **IAM** — App Runner ECR pull role, instance role (S3 chat access), GitHub Actions OIDC deploy role.
- **Secrets Manager** — optional `OPENAI_API_KEY` when `openai_api_key` is non-empty.

Variable names mirror `TF_VAR_*` / `terraform.tfvars`; see `terraform.tfvars.example`.

## Conventions

- Keep modules small and composable as the stack grows.
- Use remote state (for example S3 backend with DynamoDB locking) before any shared or production applies.
- Do not commit secrets; `*.tfvars` is gitignored (use `terraform.tfvars.example` as a template).

## Bootstrap (first time)

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set `github_repository`, `mcp_server_url`, and other values.
2. From this directory, run `terraform init` then `terraform apply` with AWS credentials that can create IAM (or apply in two phases via `.github/workflows/deploy-aws.yml`, which targets ECR first so a image exists before App Runner is created).
3. After the first successful apply, copy `terraform output -raw github_actions_role_arn` into the GitHub repository secret **`AWS_DEPLOY_ROLE_ARN`**, and set **`MCP_SERVER_URL`**, optional **`MCP_SERVER_HEADERS_JSON`** (use `{}` if unused), and optional **`OPENAI_API_KEY`** to match your `tfvars`.

## Getting started

```bash
cd infra/terraform
terraform init
terraform validate
```

Applying real resources requires AWS credentials configured for the Terraform AWS provider.
