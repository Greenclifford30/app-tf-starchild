output "orders_api_url" {
  description = "Set this exact value as NEXT_PUBLIC_ORDERS_API_URL in Amplify."
  value       = "${aws_apigatewayv2_api.orders.api_endpoint}/orders"
}

output "orders_table_name" {
  description = "DynamoDB table containing durable order requests."
  value       = aws_dynamodb_table.order_requests.name
}

output "notification_topic_arn" {
  description = "SNS topic used for operator order notifications."
  value       = aws_sns_topic.order_requests.arn
}

output "notification_confirmation_required" {
  description = "The notification address must confirm the email sent by Amazon SNS."
  value       = true
}
