output "ecr_repository_url" {
  description = "ECR repository URL (without tag) for `docker push`."
  value       = aws_ecr_repository.api.repository_url
}

output "app_runner_service_url" {
  description = "Public HTTPS URL of the API (set PUBLIC_MERIDIAN_API_BASE_URL to this value for frontend builds)."
  value       = aws_apprunner_service.api.service_url
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name (HTTPS)."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID for cache invalidation."
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_bucket_id" {
  description = "S3 bucket ID for static frontend assets."
  value       = aws_s3_bucket.frontend.id
}

output "chat_sessions_bucket_id" {
  description = "Private S3 bucket storing chat session JSON."
  value       = aws_s3_bucket.chat_sessions.id
}

output "github_actions_role_arn" {
  description = "IAM role ARN for `aws-actions/configure-aws-credentials` (repository secret AWS_DEPLOY_ROLE_ARN)."
  value       = aws_iam_role.github_actions_deploy.arn
}
