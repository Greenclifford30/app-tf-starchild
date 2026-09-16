terraform {
  required_version = ">= 1.5.0"

  required_providers {
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(var.tags, {
      Environment = var.environment
    })
  }
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

resource "aws_dynamodb_table" "order_requests" {
  name         = "${local.name_prefix}-order-requests"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "submission_id"

  attribute {
    name = "submission_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }
}

resource "aws_dynamodb_table" "products" {
  name         = "${local.name_prefix}-products"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slug"

  attribute {
    name = "slug"
    type = "S"
  }
  attribute {
    name = "catalog_status"
    type = "S"
  }
  attribute {
    name = "catalog_sort"
    type = "S"
  }

  global_secondary_index {
    name            = "catalog"
    hash_key        = "catalog_status"
    range_key       = "catalog_sort"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}

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

resource "aws_cognito_user_pool" "admins" {
  name = "${local.name_prefix}-admins"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  username_attributes = ["email"]
  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_client" "admins" {
  name         = "${local.name_prefix}-catalog-admin-client"
  user_pool_id = aws_cognito_user_pool.admins.id
  generate_secret = false
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}

resource "aws_cognito_user_group" "product_admins" {
  name         = "starchild-admin"
  user_pool_id = aws_cognito_user_pool.admins.id
}

resource "aws_sns_topic" "order_requests" {
  name = "${local.name_prefix}-order-requests"
}

resource "aws_sns_topic_subscription" "order_email" {
  topic_arn = aws_sns_topic.order_requests.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

resource "aws_iam_role" "order_lambda" {
  name = "${local.name_prefix}-order-request-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "order_lambda_logs" {
  role       = aws_iam_role.order_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "order_lambda_data" {
  name = "${local.name_prefix}-order-request-data"
  role = aws_iam_role.order_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.order_requests.arn
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem"]
        Resource = aws_dynamodb_table.products.arn
      },
      {
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.order_requests.arn
      }
    ]
  })
}

resource "aws_iam_role" "products_lambda" {
  name = "${local.name_prefix}-products-lambda"
  assume_role_policy = aws_iam_role.order_lambda.assume_role_policy
}

resource "aws_iam_role_policy_attachment" "products_lambda_logs" {
  role = aws_iam_role.products_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "products_lambda_data" {
  name = "${local.name_prefix}-products-data"
  role = aws_iam_role.products_lambda.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query", "dynamodb:Scan"], Resource = [aws_dynamodb_table.products.arn, "${aws_dynamodb_table.products.arn}/index/catalog"] },
    { Effect = "Allow", Action = ["s3:PutObject"], Resource = "${aws_s3_bucket.product_media.arn}/products/*" }
  ] })
}

data "archive_file" "order_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src/lambda/create_order"
  output_path = "${path.module}/.terraform/create_order.zip"
}

data "archive_file" "products_lambda" {
  type = "zip"
  source_dir = "${path.module}/src/lambda/products"
  output_path = "${path.module}/.terraform/products.zip"
}

resource "aws_cloudwatch_log_group" "order_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-create-order-request"
  retention_in_days = 30
}

resource "aws_lambda_function" "create_order" {
  function_name    = "${local.name_prefix}-create-order-request"
  description      = "Validates and stores Starchild MVP order requests."
  filename         = data.archive_file.order_lambda.output_path
  source_code_hash = data.archive_file.order_lambda.output_base64sha256
  role             = aws_iam_role.order_lambda.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 10

  environment {
    variables = {
      ALLOWED_ORIGINS        = join(",", var.allowed_origins)
      NOTIFICATION_TOPIC_ARN = aws_sns_topic.order_requests.arn
      ORDERS_TABLE           = aws_dynamodb_table.order_requests.name
      PRODUCTS_TABLE         = aws_dynamodb_table.products.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.order_lambda,
    aws_iam_role_policy_attachment.order_lambda_logs,
    aws_iam_role_policy.order_lambda_data
  ]
}

resource "aws_cloudwatch_log_group" "products_lambda" {
  name = "/aws/lambda/${local.name_prefix}-products"
  retention_in_days = 30
}

resource "aws_lambda_function" "products" {
  function_name = "${local.name_prefix}-products"
  description = "Serves and administers the Starchild product catalog."
  filename = data.archive_file.products_lambda.output_path
  source_code_hash = data.archive_file.products_lambda.output_base64sha256
  role = aws_iam_role.products_lambda.arn
  handler = "lambda_function.lambda_handler"
  runtime = "python3.13"
  architectures = ["arm64"]
  memory_size = 256
  timeout = 10
  environment {
    variables = {
      ALLOWED_ORIGINS = join(",", var.allowed_origins)
      PRODUCTS_TABLE  = aws_dynamodb_table.products.name
      MEDIA_BUCKET    = aws_s3_bucket.product_media.id
      MEDIA_BASE_URL  = "https://${aws_cloudfront_distribution.product_media.domain_name}"
    }
  }
  depends_on = [aws_cloudwatch_log_group.products_lambda, aws_iam_role_policy_attachment.products_lambda_logs, aws_iam_role_policy.products_lambda_data]
}

resource "aws_cloudwatch_log_group" "orders_api" {
  name              = "/aws/apigateway/${local.name_prefix}-orders"
  retention_in_days = 30
}

resource "aws_apigatewayv2_api" "orders" {
  name          = "${local.name_prefix}-orders"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type", "authorization"]
    allow_methods = ["OPTIONS", "GET", "POST", "PUT", "DELETE"]
    allow_origins = var.allowed_origins
    max_age       = 86400
  }
}

resource "aws_apigatewayv2_authorizer" "product_admin" {
  api_id = aws_apigatewayv2_api.orders.id
  authorizer_type = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name = "product-admin"
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.admins.id]
    issuer = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.admins.id}"
  }
}

resource "aws_apigatewayv2_integration" "products" {
  api_id = aws_apigatewayv2_api.orders.id
  integration_type = "AWS_PROXY"
  integration_uri = aws_lambda_function.products.invoke_arn
  integration_method = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds = 10000
}

resource "aws_apigatewayv2_route" "get_products" {
  api_id    = aws_apigatewayv2_api.orders.id
  route_key = "GET /products"
  target    = "integrations/${aws_apigatewayv2_integration.products.id}"
}

resource "aws_apigatewayv2_route" "get_product" {
  api_id    = aws_apigatewayv2_api.orders.id
  route_key = "GET /products/{slug}"
  target    = "integrations/${aws_apigatewayv2_integration.products.id}"
}

resource "aws_apigatewayv2_route" "admin_products" {
  api_id = aws_apigatewayv2_api.orders.id
  route_key = "GET /admin/products"
  target = "integrations/${aws_apigatewayv2_integration.products.id}"
  authorization_type = "JWT"
  authorizer_id = aws_apigatewayv2_authorizer.product_admin.id
}

resource "aws_apigatewayv2_route" "create_product" {
  api_id             = aws_apigatewayv2_api.orders.id
  route_key          = "POST /products"
  target             = "integrations/${aws_apigatewayv2_integration.products.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.product_admin.id
}

resource "aws_apigatewayv2_route" "update_product" {
  api_id             = aws_apigatewayv2_api.orders.id
  route_key          = "PUT /products/{slug}"
  target             = "integrations/${aws_apigatewayv2_integration.products.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.product_admin.id
}

resource "aws_apigatewayv2_route" "archive_product" {
  api_id             = aws_apigatewayv2_api.orders.id
  route_key          = "DELETE /products/{slug}"
  target             = "integrations/${aws_apigatewayv2_integration.products.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.product_admin.id
}

resource "aws_apigatewayv2_route" "product_upload" {
  api_id             = aws_apigatewayv2_api.orders.id
  route_key          = "POST /product-images/upload-url"
  target             = "integrations/${aws_apigatewayv2_integration.products.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.product_admin.id
}

resource "aws_apigatewayv2_integration" "create_order" {
  api_id                 = aws_apigatewayv2_api.orders.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.create_order.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 10000
}

resource "aws_apigatewayv2_route" "create_order" {
  api_id    = aws_apigatewayv2_api.orders.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.create_order.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.orders.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 10
    throttling_rate_limit  = 5
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.orders_api.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowOrdersApiInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_order.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orders.execution_arn}/*/*"
}

resource "aws_lambda_permission" "products_api_gateway" {
  statement_id = "AllowProductsApiInvocation"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.products.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.orders.execution_arn}/*/*"
}
