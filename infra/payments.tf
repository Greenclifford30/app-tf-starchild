# Secret values are provisioned separately with AWS Secrets Manager; they never enter Terraform state.
resource "aws_secretsmanager_secret" "stripe" {
  count       = var.stripe_payments_enabled ? 1 : 0
  name        = "${local.name_prefix}-stripe-payments"
  description = "JSON containing Stripe secret_key and webhook_secret."
}

# Dependency artifact is checked in so remote plan and apply workers both receive it.
resource "aws_lambda_layer_version" "payments" {
  count                    = var.stripe_payments_enabled ? 1 : 0
  layer_name               = "${local.name_prefix}-stripe-sdk"
  filename                 = "${path.module}/artifacts/stripe-python-3.13-arm64.zip"
  source_code_hash         = filebase64sha256("${path.module}/artifacts/stripe-python-3.13-arm64.zip")
  compatible_runtimes      = ["python3.13"]
  compatible_architectures = ["arm64"]
}

# Package project code independently so it tracks source edits without rebuilding dependencies.
data "archive_file" "payment_helpers" {
  count       = var.stripe_payments_enabled ? 1 : 0
  type        = "zip"
  output_path = "${path.module}/.terraform/payment-helpers.zip"
  source {
    content  = file("${path.module}/src/payment_layer/starchild_stripe.py")
    filename = "python/starchild_stripe.py"
  }
  source {
    content  = file("${path.module}/src/lambda/create_order/lambda_function.py")
    filename = "python/order_validation.py"
  }
}
resource "aws_lambda_layer_version" "payment_helpers" {
  count                    = var.stripe_payments_enabled ? 1 : 0
  layer_name               = "${local.name_prefix}-payment-helpers"
  filename                 = data.archive_file.payment_helpers[0].output_path
  source_code_hash         = data.archive_file.payment_helpers[0].output_base64sha256
  compatible_runtimes      = ["python3.13"]
  compatible_architectures = ["arm64"]
}
resource "aws_iam_role" "payments" {
  count              = var.stripe_payments_enabled ? 1 : 0
  name               = "${local.name_prefix}-payments-lambda"
  assume_role_policy = aws_iam_role.order_lambda.assume_role_policy
}
resource "aws_iam_role_policy_attachment" "payments_logs" {
  count      = var.stripe_payments_enabled ? 1 : 0
  role       = aws_iam_role.payments[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy" "payments" {
  count = var.stripe_payments_enabled ? 1 : 0
  role  = aws_iam_role.payments[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"], Resource = [aws_dynamodb_table.order_requests.arn, "${aws_dynamodb_table.order_requests.arn}/index/review", aws_dynamodb_table.confirmed_orders.arn, "${aws_dynamodb_table.confirmed_orders.arn}/index/all-orders", aws_dynamodb_table.customer_notifications.arn, aws_dynamodb_table.products.arn] },
      { Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = aws_secretsmanager_secret.stripe[0].arn },
      { Effect = "Allow", Action = "sns:Publish", Resource = aws_sns_topic.customer_notification_alerts.arn }
    ]
  })
}
resource "aws_iam_role_policy" "admin_stripe_secret" {
  count = var.stripe_payments_enabled ? 1 : 0
  role  = aws_iam_role.admin_orders.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = aws_secretsmanager_secret.stripe[0].arn }
  ] })
}
data "archive_file" "payments" {
  count       = var.stripe_payments_enabled ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/src/lambda/payments"
  output_path = "${path.module}/.terraform/payments.zip"
  excludes    = ["__pycache__"]
}
resource "aws_cloudwatch_log_group" "payments" {
  count             = var.stripe_payments_enabled ? 1 : 0
  name              = "/aws/lambda/${local.name_prefix}-payments"
  retention_in_days = 30
}
resource "aws_lambda_function" "payments" {
  count            = var.stripe_payments_enabled ? 1 : 0
  function_name    = "${local.name_prefix}-payments"
  role             = aws_iam_role.payments[0].arn
  filename         = data.archive_file.payments[0].output_path
  source_code_hash = data.archive_file.payments[0].output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  layers           = [aws_lambda_layer_version.payments[0].arn, aws_lambda_layer_version.payment_helpers[0].arn]
  timeout          = 25
  memory_size      = 256
  environment {
    variables = {
      REQUESTS_TABLE               = aws_dynamodb_table.order_requests.name
      ORDERS_TABLE                 = aws_dynamodb_table.order_requests.name
      CONFIRMED_ORDERS_TABLE       = aws_dynamodb_table.confirmed_orders.name
      PRODUCTS_TABLE               = aws_dynamodb_table.products.name
      CUSTOMER_NOTIFICATIONS_TABLE = aws_dynamodb_table.customer_notifications.name
      STRIPE_SECRET_ARN            = aws_secretsmanager_secret.stripe[0].arn
      STRIPE_APPAREL_TAX_CODE      = var.stripe_apparel_tax_code
      ALLOWED_ORIGINS              = join(",", local.cors_allowed_origins)
      PAYMENT_ALERT_TOPIC_ARN      = aws_sns_topic.customer_notification_alerts.arn
    }
  }
  lifecycle {
    precondition {
      condition     = can(regex("^txcd_[0-9]+$", var.stripe_apparel_tax_code))
      error_message = "Set a Stripe apparel tax code when payments are enabled."
    }
  }
  depends_on = [aws_cloudwatch_log_group.payments, aws_iam_role_policy.payments, aws_iam_role_policy_attachment.payments_logs]
}
resource "aws_apigatewayv2_integration" "payments" {
  count                  = var.stripe_payments_enabled ? 1 : 0
  api_id                 = aws_apigatewayv2_api.orders.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.payments[0].invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}
resource "aws_apigatewayv2_route" "payments" {
  for_each  = var.stripe_payments_enabled ? toset(["POST /checkout/sessions", "GET /checkout/sessions/{id}", "POST /stripe/webhook"]) : toset([])
  api_id    = aws_apigatewayv2_api.orders.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.payments[0].id}"
}
resource "aws_lambda_permission" "payments_api" {
  count         = var.stripe_payments_enabled ? 1 : 0
  statement_id  = "AllowPaymentsApiInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payments[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.orders.execution_arn}/*/*"
}
resource "aws_cloudwatch_event_rule" "payment_expiry" {
  count               = var.stripe_payments_enabled ? 1 : 0
  name                = "${local.name_prefix}-payment-expiry"
  schedule_expression = "rate(6 hours)"
}
resource "aws_cloudwatch_event_target" "payment_expiry" {
  count = var.stripe_payments_enabled ? 1 : 0
  rule  = aws_cloudwatch_event_rule.payment_expiry[0].name
  arn   = aws_lambda_function.payments[0].arn
}
resource "aws_lambda_permission" "payment_expiry" {
  count         = var.stripe_payments_enabled ? 1 : 0
  statement_id  = "AllowPaymentExpirySchedule"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.payments[0].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.payment_expiry[0].arn
}
resource "aws_cloudwatch_metric_alarm" "payments_errors" {
  count               = var.stripe_payments_enabled ? 1 : 0
  alarm_name          = "${local.name_prefix}-payment-lambda-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = aws_lambda_function.payments[0].function_name }
  alarm_actions       = [aws_sns_topic.customer_notification_alerts.arn]
}
output "payments_api_url" {
  value       = local.public_api_base_url
  description = "Base URL for NEXT_PUBLIC_PAYMENTS_API_URL."
}
output "stripe_secret_arn" {
  value       = try(aws_secretsmanager_secret.stripe[0].arn, null)
  description = "Provision secret_key and webhook_secret JSON directly in Secrets Manager."
}
output "stripe_webhook_url" {
  value = var.stripe_payments_enabled ? "${local.public_api_base_url}/stripe/webhook" : null
}

resource "aws_cloudwatch_metric_alarm" "payments_api_errors" {
  count               = var.stripe_payments_enabled ? 1 : 0
  alarm_name          = "${local.name_prefix}-payment-api-errors"
  namespace           = "AWS/ApiGateway"
  metric_name         = "5xx"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { ApiId = aws_apigatewayv2_api.orders.id }
  alarm_actions       = [aws_sns_topic.customer_notification_alerts.arn]
}
