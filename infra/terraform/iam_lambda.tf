resource "aws_iam_role" "lambda_execution" {
  name = "${local.name_prefix}-lambda-api"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "lambda_instance" {
  statement {
    sid = "ChatSessionsS3Objects"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = ["${aws_s3_bucket.chat_sessions.arn}/sessions/*"]
  }

  statement {
    sid       = "ChatSessionsS3List"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.chat_sessions.arn]
    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["sessions/*"]
    }
  }
}

resource "aws_iam_role_policy" "lambda_instance" {
  name   = "${local.name_prefix}-lambda-api-inline"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_instance.json
}

data "aws_iam_policy_document" "lambda_openai_secret" {
  count = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0

  statement {
    sid       = "OpenAiSecretRead"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.openai_api_key[0].arn]
  }
}

resource "aws_iam_role_policy" "lambda_openai_secret" {
  count = length(trimspace(var.openai_api_key)) > 0 ? 1 : 0

  name   = "${local.name_prefix}-lambda-openai-secret"
  role   = aws_iam_role.lambda_execution.id
  policy = data.aws_iam_policy_document.lambda_openai_secret[0].json
}
