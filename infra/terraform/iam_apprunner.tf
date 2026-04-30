resource "aws_iam_role" "apprunner_ecr_access" {
  name = "${local.name_prefix}-apprunner-ecr"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "build.apprunner.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_iam_role" "apprunner_instance" {
  name = "${local.name_prefix}-apprunner-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "tasks.apprunner.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

data "aws_iam_policy_document" "apprunner_instance" {
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

resource "aws_iam_role_policy" "apprunner_instance" {
  name   = "${local.name_prefix}-apprunner-instance-inline"
  role   = aws_iam_role.apprunner_instance.id
  policy = data.aws_iam_policy_document.apprunner_instance.json
}
