output "orders_api_url" {
  description = "Set this exact value as NEXT_PUBLIC_ORDERS_API_URL in Amplify."
  value       = "${aws_apigatewayv2_api.orders.api_endpoint}/orders"
}

output "products_api_url" {
  description = "Set this exact value as PRODUCTS_API_URL in Amplify."
  value       = aws_apigatewayv2_api.orders.api_endpoint
}

output "products_table_name" {
  value = aws_dynamodb_table.products.name
}

output "product_media_bucket_name" {
  value = aws_s3_bucket.product_media.id
}

output "product_media_url" {
  description = "CloudFront base URL for product images."
  value       = "https://${aws_cloudfront_distribution.product_media.domain_name}"
}

output "product_admin_user_pool_id" {
  value = aws_cognito_user_pool.admins.id
}

output "product_admin_client_id" {
  value = aws_cognito_user_pool_client.admins.id
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
