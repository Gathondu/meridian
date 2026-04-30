locals {
  name_prefix = replace(lower(var.project_name), "_", "-")

  cloudfront_origin_id = "s3-frontend"

  # App Runner public URL is unknown until after apply; CORS uses CloudFront URL once known.
  cors_for_app = trimspace(join(",", compact([
    "https://${aws_cloudfront_distribution.frontend.domain_name}",
    trimspace(var.cors_origins_extra)
  ])))
}
