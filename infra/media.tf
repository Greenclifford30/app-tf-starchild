resource "aws_s3_bucket" "product_media" {
  bucket_prefix = "${local.name_prefix}-product-media-"
}

resource "aws_s3_bucket_public_access_block" "product_media" {
  bucket                  = aws_s3_bucket.product_media.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "product_media" {
  bucket = aws_s3_bucket.product_media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "product_media" {
  bucket = aws_s3_bucket.product_media.id
  cors_rule {
    allowed_headers = ["content-type"]
    allowed_methods = ["PUT"]
    allowed_origins = var.allowed_origins
    expose_headers  = ["etag"]
    max_age_seconds = 900
  }
}

resource "aws_cloudfront_origin_access_control" "product_media" {
  name                              = "${local.name_prefix}-product-media"
  description                       = "CloudFront access to Starchild product media"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "product_media" {
  enabled             = true
  comment             = "Starchild product media"
  default_root_object = ""

  origin {
    domain_name              = aws_s3_bucket.product_media.bucket_regional_domain_name
    origin_id                = "product-media"
    origin_access_control_id = aws_cloudfront_origin_access_control.product_media.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "product-media"
    viewer_protocol_policy = "redirect-to-https"
    compress = true
    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "product_media_bucket" {
  statement {
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.product_media.arn}/*"]
    condition {
      test = "StringEquals"
      variable = "AWS:SourceArn"
      values = [aws_cloudfront_distribution.product_media.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "product_media" {
  bucket = aws_s3_bucket.product_media.id
  policy = data.aws_iam_policy_document.product_media_bucket.json
}
