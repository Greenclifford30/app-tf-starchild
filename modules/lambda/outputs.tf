output "lambda_functions" {
  description = "Map of Lambda function details"
  value = {
    for k, v in aws_lambda_function.functions : k => {
      function_name = v.function_name
      function_arn  = v.arn
      invoke_arn    = v.invoke_arn
    }
  }
}

output "function_names" {
  description = "Names of created Lambda functions"
  value       = [for f in aws_lambda_function.functions : f.function_name]
}

output "function_arns" {
  description = "ARNs of created Lambda functions"
  value       = [for f in aws_lambda_function.functions : f.arn]
}

output "execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution.arn
}