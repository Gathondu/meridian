resource "aws_apprunner_service" "api" {
  service_name = "${local.name_prefix}-api"

  source_configuration {
    auto_deployments_enabled = true

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"

      image_configuration {
        port = "8000"

        runtime_environment_variables = merge(
          {
            MCP_SERVER_URL            = var.mcp_server_url
            MCP_SERVER_HEADERS        = local.mcp_server_headers_effective
            CORS_ORIGINS              = local.cors_for_app
            LOG_LEVEL                 = var.log_level
            LOG_JSON                  = tostring(var.log_json)
            RATE_LIMIT_DEFAULT        = var.rate_limit_default
            REQUEST_ID_HEADER         = var.request_id_header
            OPENAI_MODEL              = var.openai_model
            CHAT_SESSIONS_S3_BUCKET   = aws_s3_bucket.chat_sessions.bucket
            CHAT_SESSIONS_S3_PREFIX   = "sessions"
            AWS_DEFAULT_REGION        = var.aws_region
            AWS_REGION                = var.aws_region
          },
          length(trimspace(var.openai_base_url)) > 0 ? { OPENAI_BASE_URL = var.openai_base_url } : {},
        )

        runtime_environment_secrets = length(trimspace(var.openai_api_key)) > 0 ? {
          OPENAI_API_KEY = aws_secretsmanager_secret.openai_api_key[0].arn
        } : {}
      }
    }
  }

  instance_configuration {
    cpu               = "1024"
    memory            = "2048"
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  depends_on = [
    aws_iam_role_policy_attachment.apprunner_ecr_access,
    aws_iam_role_policy.apprunner_instance,
    aws_cloudfront_distribution.frontend,
  ]
}
