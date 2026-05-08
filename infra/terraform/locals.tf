locals {
  name_prefix = replace(lower(var.project_name), "_", "-")

  cloudfront_origin_id = "s3-frontend"

  mcp_server_headers_effective = trimspace(var.mcp_server_headers_json) == "" ? "{}" : var.mcp_server_headers_json

  # The public API URL is unknown until after apply; CORS uses CloudFront URL once known.
  cors_for_app = trimspace(join(",", compact([
    "https://${aws_cloudfront_distribution.frontend.domain_name}",
    trimspace(var.cors_origins_extra)
  ])))
}
