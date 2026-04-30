resource "aws_secretsmanager_secret_policy" "openai_api_key" {
  count = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0

  secret_arn = aws_secretsmanager_secret.openai_api_key[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowAppRunnerRead"
      Effect = "Allow"
      Principal = {
        Service = "apprunner.amazonaws.com"
      }
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.openai_api_key[0].arn
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}
