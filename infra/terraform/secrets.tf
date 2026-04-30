resource "aws_secretsmanager_secret" "openai_api_key" {
  count = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0
  name  = "${local.name_prefix}/openai-api-key"
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  count         = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0
  secret_id     = aws_secretsmanager_secret.openai_api_key[0].id
  secret_string = var.openai_api_key
}
