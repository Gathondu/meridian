resource "aws_lambda_function" "api" {
  function_name = "${local.name_prefix}-api"
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"

  architectures = ["x86_64"]
  memory_size   = 2048
  timeout       = 900

  environment {
    variables = merge(
      {
        AWS_LWA_PORT                 = "8000"
        AWS_LWA_READINESS_CHECK_PATH = "/health"
        AWS_LWA_INVOKE_MODE          = "response_stream"
        MCP_SERVER_URL               = var.mcp_server_url
        MCP_SERVER_HEADERS           = local.mcp_server_headers_effective
        CORS_ORIGINS                 = local.cors_for_app
        LOG_LEVEL                    = var.log_level
        LOG_JSON                     = tostring(var.log_json)
        RATE_LIMIT_DEFAULT           = var.rate_limit_default
        REQUEST_ID_HEADER            = var.request_id_header
        OPENAI_MODEL                 = var.openai_model
        CHAT_SESSIONS_S3_BUCKET      = aws_s3_bucket.chat_sessions.bucket
        CHAT_SESSIONS_S3_PREFIX      = "sessions"
      },
      length(trimspace(var.openai_base_url)) > 0 ? { OPENAI_BASE_URL = var.openai_base_url } : {},
      length(trimspace(var.openai_api_key)) > 0 ? { OPENAI_API_KEY_SECRET_ARN = aws_secretsmanager_secret.openai_api_key[0].arn } : {},
    )
  }

  depends_on = [
    aws_cloudfront_distribution.frontend,
    aws_ecr_repository_policy.api_lambda,
    aws_iam_role_policy.lambda_instance,
    aws_iam_role_policy_attachment.lambda_basic_execution,
  ]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  cors {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "HEAD", "POST"]
    allow_origins     = local.lambda_function_url_cors_origins
    expose_headers    = [var.request_id_header]
    max_age           = 300
  }
}

resource "aws_lambda_permission" "api_function_url_public" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}
