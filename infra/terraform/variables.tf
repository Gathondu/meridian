variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "eu-central-1"
}

variable "project_name" {
  type        = string
  description = "Short name prefix for buckets, roles, and App Runner service."
  default     = "meridian"
}

variable "github_repository" {
  type        = string
  description = "GitHub repository allowed to assume the deploy role (format: owner/repo)."
}

variable "github_oidc_thumbprints" {
  type        = list(string)
  description = "TLS thumbprints for token.actions.githubusercontent.com (GitHub publishes updates periodically)."
  default     = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1c58a3a8518e8759bf075b76b750d4f2df264fcd"]
}

# --- Application env (mirror backend/.env.example; supply via tfvars or TF_VAR_*) ---

variable "mcp_server_url" {
  type        = string
  description = "Streamable HTTP MCP endpoint (MCP_SERVER_URL)."
}

variable "mcp_server_headers_json" {
  type        = string
  description = "Optional JSON object for outbound MCP headers (MCP_SERVER_HEADERS)."
  default     = "{}"
  sensitive   = true
}

variable "cors_origins_extra" {
  type        = string
  description = "Optional comma-separated extra CORS origins (e.g. http://localhost:5173 for dev)."
  default     = ""
}

variable "log_level" {
  type        = string
  default     = "INFO"
}

variable "log_json" {
  type        = bool
  default     = true
}

variable "rate_limit_default" {
  type        = string
  default     = "120/minute"
}

variable "request_id_header" {
  type        = string
  default     = "X-Request-ID"
}

variable "openai_model" {
  type        = string
  default     = "gpt-4o-mini"
}

variable "openai_base_url" {
  type        = string
  description = "Optional OpenAI-compatible base URL (OPENAI_BASE_URL); empty to use default OpenAI."
  default     = ""
}

variable "openai_api_key" {
  type        = string
  description = "OpenAI API key; stored in Secrets Manager and injected into App Runner (OPENAI_API_KEY). Use TF_VAR_openai_api_key in CI."
  default     = ""
  sensitive   = true
}
