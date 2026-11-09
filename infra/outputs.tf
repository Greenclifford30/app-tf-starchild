locals {
  public_api_base_url = var.enable_api_custom_domain ? "https://${aws_apigatewayv2_domain_name.api[0].domain_name}" : aws_apigatewayv2_api.orders.api_endpoint
}

output "orders_api_url" {
  description = "Set this exact value as NEXT_PUBLIC_ORDERS_API_URL in Amplify."
  value       = "${local.public_api_base_url}/orders"
}

output "products_api_url" {
  description = "Set this exact value as PRODUCTS_API_URL in Amplify."
  value       = local.public_api_base_url
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
  description = "SNS topic retained during the notification cutover, if enabled."
  value       = try(aws_sns_topic.order_requests[0].arn, null)
}

output "notification_confirmation_required" {
  description = "Whether the retained SNS subscription requires recipient confirmation."
  value       = var.retain_sns_notifications
}

output "notification_ses_dns_records" {
  description = "DNS records required to verify the notification sending domain and enable DKIM."
  value = concat([
    {
      name  = "_amazonses.${aws_ses_domain_identity.notifications.domain}"
      type  = "TXT"
      value = aws_ses_domain_identity.notifications.verification_token
    }
    ], [for token in aws_ses_domain_dkim.notifications.dkim_tokens : {
      name  = "${token}._domainkey.${aws_ses_domain_identity.notifications.domain}"
      type  = "CNAME"
      value = "${token}.dkim.amazonses.com"
  }])
}

output "customer_notifications_table_name" {
  description = "Customer email outbox for delivery status and retry."
  value       = aws_dynamodb_table.customer_notifications.name
}

output "customer_notification_failure_queue_url" {
  description = "Queue containing exhausted customer email stream failures."
  value       = aws_sqs_queue.customer_notifications_failed.url
}
