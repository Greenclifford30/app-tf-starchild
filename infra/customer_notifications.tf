resource "aws_dynamodb_table" "customer_notifications" {
  name             = "${local.name_prefix}-customer-notifications"
  billing_mode     = "PAY_PER_REQUEST"
  hash_key         = "notification_id"
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  attribute {
    name = "notification_id"
    type = "S"
  }
  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}

resource "aws_sqs_queue" "customer_notifications_failed" {
  name                      = "${local.name_prefix}-customer-notification-failures"
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true
}

resource "aws_sns_topic" "customer_notification_alerts" {
  name = "${local.name_prefix}-customer-notification-alerts"
}
resource "aws_sns_topic_subscription" "customer_notification_alerts" {
  topic_arn = aws_sns_topic.customer_notification_alerts.arn
  protocol  = "email"
  endpoint  = var.notification_email
}
resource "aws_cloudwatch_metric_alarm" "customer_notification_failures" {
  alarm_name          = "${local.name_prefix}-customer-notification-failures"
  alarm_description   = "Customer email delivery exhausted its retries; inspect the outbox and failure queue."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { QueueName = aws_sqs_queue.customer_notifications_failed.name }
  alarm_actions       = [aws_sns_topic.customer_notification_alerts.arn]
}

resource "aws_iam_role" "customer_notifications" {
  name               = "${local.name_prefix}-customer-notifications"
  assume_role_policy = aws_iam_role.order_lambda.assume_role_policy
}
resource "aws_iam_role_policy_attachment" "customer_notifications_logs" {
  role       = aws_iam_role.customer_notifications.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}
resource "aws_iam_role_policy" "customer_notifications" {
  role = aws_iam_role.customer_notifications.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["dynamodb:DescribeStream", "dynamodb:GetRecords", "dynamodb:GetShardIterator", "dynamodb:ListStreams"], Resource = aws_dynamodb_table.customer_notifications.stream_arn },
      { Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:UpdateItem"], Resource = aws_dynamodb_table.customer_notifications.arn },
      { Effect = "Allow", Action = "ses:SendEmail", Resource = aws_ses_domain_identity.notifications.arn },
      { Effect = "Allow", Action = "sqs:SendMessage", Resource = aws_sqs_queue.customer_notifications_failed.arn }
    ]
  })
}
data "archive_file" "customer_notifications" {
  type        = "zip"
  source_dir  = "${path.module}/src/lambda/customer_notifications"
  output_path = "${path.module}/.terraform/customer_notifications.zip"
  excludes    = ["__pycache__"]
}
resource "aws_cloudwatch_log_group" "customer_notifications" {
  name              = "/aws/lambda/${local.name_prefix}-customer-notifications"
  retention_in_days = 30
}
resource "aws_lambda_function" "customer_notifications" {
  function_name    = "${local.name_prefix}-customer-notifications"
  role             = aws_iam_role.customer_notifications.arn
  filename         = data.archive_file.customer_notifications.output_path
  source_code_hash = data.archive_file.customer_notifications.output_base64sha256
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  timeout          = 30
  environment {
    variables = {
      CUSTOMER_NOTIFICATIONS_TABLE = aws_dynamodb_table.customer_notifications.name
      NOTIFICATION_FROM            = "Starchild <orders@starchildclo.com>"
    }
  }
  depends_on = [aws_cloudwatch_log_group.customer_notifications, aws_iam_role_policy.customer_notifications, aws_iam_role_policy_attachment.customer_notifications_logs]
}
resource "aws_lambda_event_source_mapping" "customer_notifications" {
  event_source_arn                   = aws_dynamodb_table.customer_notifications.stream_arn
  function_name                      = aws_lambda_function.customer_notifications.arn
  starting_position                  = "TRIM_HORIZON"
  batch_size                         = 1
  maximum_retry_attempts             = 5
  function_response_types            = ["ReportBatchItemFailures"]
  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.customer_notifications_failed.arn
    }
  }
}
