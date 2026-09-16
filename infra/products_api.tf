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

data "archive_file" "products_lambda" {
  type = "zip"
  source_dir = "${path.module}/src/lambda/products"
  output_path = "${path.module}/.terraform/products.zip"
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

resource "aws_lambda_permission" "products_api_gateway" {
  statement_id = "AllowProductsApiInvocation"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.products.function_name
  principal = "apigateway.amazonaws.com"
  source_arn = "${aws_apigatewayv2_api.orders.execution_arn}/*/*"
}
