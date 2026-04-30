resource "aws_s3_bucket" "chat_sessions" {
  bucket_prefix = "${local.name_prefix}-chat-"

  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "chat_sessions" {
  bucket = aws_s3_bucket.chat_sessions.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "chat_sessions" {
  bucket = aws_s3_bucket.chat_sessions.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
