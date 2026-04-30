resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com",
  ]

  thumbprint_list = var.github_oidc_thumbprints
}

resource "aws_iam_role" "github_actions_deploy" {
  name = "${local.name_prefix}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = "sts:AssumeRoleWithWebIdentity"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
        }
      }
    }]
  })
}

# Broad policy for `terraform apply` from CI (use a dedicated AWS account in production).
data "aws_iam_policy_document" "github_actions_terraform" {
  statement {
    sid    = "MeridianDeployFromGitHubActions"
    effect = "Allow"
    actions = [
      "iam:*",
      "ecr:GetAuthorizationToken",
      "ecr:*",
      "s3:*",
      "cloudfront:*",
      "secretsmanager:*",
      "apprunner:*",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_actions_terraform" {
  name   = "${local.name_prefix}-github-terraform"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_actions_terraform.json
}
