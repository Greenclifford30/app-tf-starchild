# Confirmed orders and immutable workflow events share a table but not an item.
resource "aws_dynamodb_table" "confirmed_orders" {
  name         = "${local.name_prefix}-confirmed-orders"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }
  attribute {
    name = "sk"
    type = "S"
  }
  attribute {
    name = "all_pk"
    type = "S"
  }
  attribute {
    name = "status_pk"
    type = "S"
  }
  attribute {
    name = "fulfillment_pk"
    type = "S"
  }
  attribute {
    name = "index_sort"
    type = "S"
  }
  global_secondary_index {
    name               = "all-orders"
    hash_key           = "all_pk"
    range_key          = "index_sort"
    projection_type    = "INCLUDE"
    non_key_attributes = ["order_id", "order_number", "created_at", "order_status", "payment_status", "fulfillment_status", "fulfillment_method", "total_cents", "currency", "refund_follow_up"]
  }
  global_secondary_index {
    name               = "by-status"
    hash_key           = "status_pk"
    range_key          = "index_sort"
    projection_type    = "INCLUDE"
    non_key_attributes = ["order_id", "order_number", "created_at", "order_status", "payment_status", "fulfillment_status", "fulfillment_method", "total_cents", "currency", "refund_follow_up"]
  }
  global_secondary_index {
    name               = "by-fulfillment"
    hash_key           = "fulfillment_pk"
    range_key          = "index_sort"
    projection_type    = "INCLUDE"
    non_key_attributes = ["order_id", "order_number", "created_at", "order_status", "payment_status", "fulfillment_status", "fulfillment_method", "total_cents", "currency", "refund_follow_up"]
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}

resource "aws_iam_role" "admin_orders" {
  name               = "${local.name_prefix}-admin-orders-lambda"
  assume_role_policy = aws_iam_role.order_lambda.assume_role_policy
}
resource "aws_iam_role_policy_attachment" "admin_orders_logs" {
  role       = aws_iam_role.admin_orders.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy" "admin_orders_data" {
  name = "${local.name_prefix}-admin-orders-data"
  role = aws_iam_role.admin_orders.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem", "dynamodb:Query"], Resource = [aws_dynamodb_table.order_requests.arn, "${aws_dynamodb_table.order_requests.arn}/index/review"] },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"], Resource = [aws_dynamodb_table.confirmed_orders.arn, "${aws_dynamodb_table.confirmed_orders.arn}/index/*"] },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:ConditionCheckItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.products.arn },
      { Effect = "Allow", Action = ["dynamodb:PutItem"], Resource = aws_dynamodb_table.customer_notifications.arn }
    ]
  })
}
data "archive_file" "admin_orders" {
  type        = "zip"
  source_dir  = "${path.module}/src/lambda/admin_orders"
  output_path = "${path.module}/.terraform/admin_orders.zip"
  excludes    = ["__pycache__"]
}
resource "aws_cloudwatch_log_group" "admin_orders" {
  name              = "/aws/lambda/${local.name_prefix}-admin-orders"
  retention_in_days = 30
}
resource "aws_lambda_function" "admin_orders" {
  function_name    = "${local.name_prefix}-admin-orders"
  description      = "Manages order requests and confirmed orders."
  filename         = data.archive_file.admin_orders.output_path
  source_code_hash = data.archive_file.admin_orders.output_base64sha256
  role             = aws_iam_role.admin_orders.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 25
  layers           = concat([aws_lambda_layer_version.inventory_helpers.arn], var.stripe_payments_enabled ? [aws_lambda_layer_version.payments[0].arn, aws_lambda_layer_version.payment_helpers[0].arn] : [])
  environment {
    variables = {
      ALLOWED_ORIGINS              = join(",", local.cors_allowed_origins)
      REQUESTS_TABLE               = aws_dynamodb_table.order_requests.name
      CONFIRMED_ORDERS_TABLE       = aws_dynamodb_table.confirmed_orders.name
      PRODUCTS_TABLE               = aws_dynamodb_table.products.name
      CUSTOMER_NOTIFICATIONS_TABLE = aws_dynamodb_table.customer_notifications.name
      PAYMENT_INSTRUCTIONS         = var.payment_instructions
      MANUAL_INVENTORY_ENABLED     = tostring(var.manual_order_inventory_enabled)
      STRIPE_SECRET_ARN            = try(aws_secretsmanager_secret.stripe[0].arn, "")
    }
  }
  depends_on = [aws_cloudwatch_log_group.admin_orders, aws_iam_role_policy_attachment.admin_orders_logs, aws_iam_role_policy.admin_orders_data]
}
resource "aws_apigatewayv2_integration" "admin_orders" {
  api_id                 = aws_apigatewayv2_api.orders.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.admin_orders.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}
resource "aws_apigatewayv2_route" "admin_orders" {
  for_each = toset([
    "GET /admin/order-requests",
    "GET /admin/order-requests/{id}",
    "POST /admin/order-requests/{id}/confirm",
    "POST /admin/order-requests/{id}/decline",
    "GET /admin/orders",
    "GET /admin/orders/{id}",
    "GET /admin/orders/{id}/events",
    "POST /admin/orders/{id}/actions"
  ])
  api_id             = aws_apigatewayv2_api.orders.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.admin_orders.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.product_admin.id
}
resource "aws_lambda_permission" "admin_orders_api_gateway" {
  statement_id  = "AllowAdminOrdersApiInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.admin_orders.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orders.execution_arn}/*/*"
}
output "confirmed_orders_table_name" {
  description = "DynamoDB table containing confirmed orders and order events."
  value       = aws_dynamodb_table.confirmed_orders.name
}
