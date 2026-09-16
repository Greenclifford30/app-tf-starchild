resource "aws_dynamodb_table" "order_requests" {
  name         = "${local.name_prefix}-order-requests"
  billing_mode = "PAY_PER_REQUEST"

  key_schema {
    attribute_name = "submission_id"
    key_type       = "HASH"
  }

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

data "archive_file" "order_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src/lambda/create_order"
  output_path = "${path.module}/.terraform/create_order.zip"
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
