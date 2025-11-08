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