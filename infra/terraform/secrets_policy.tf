resource "aws_secretsmanager_secret_policy" "openai_api_key" {
  count = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0

  secret_arn = aws_secretsmanager_secret.openai_api_key[0].arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AllowLambdaRead"
      Effect = "Allow"
      Principal = {
        AWS = aws_iam_role.lambda_execution.arn
      }
      Action   = "secretsmanager:GetSecretValue"
      Resource = aws_secretsmanager_secret.openai_api_key[0].arn
    }]
  })
}
