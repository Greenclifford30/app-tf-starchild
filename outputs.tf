output "spa_bucket_name" {
  description = "Name of the S3 bucket hosting the SPA"
  value       = module.spa.bucket_name
}

output "spa_cloudfront_url" {
  description = "CloudFront distribution URL for the SPA"
  value       = module.spa.cloudfront_url
}

output "spa_cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.spa.cloudfront_domain_name
}

output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = module.api_gateway.api_gateway_url
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = module.api_gateway.api_gateway_id
}

output "lambda_function_names" {
  description = "Names of created Lambda functions"
  value       = module.lambda_functions.function_names
}

output "lambda_function_arns" {
  description = "ARNs of created Lambda functions"
  value       = module.lambda_functions.function_arns
}