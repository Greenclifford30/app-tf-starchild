variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "api_gateway_id" {
  description = "API Gateway ID"
  type        = string
}

variable "api_gateway_execution_arn" {
  description = "API Gateway execution ARN"
  type        = string
}

variable "functions" {
  description = "Map of Lambda functions to create"
  type = map(object({
    description     = string
    handler        = string
    runtime        = string
    timeout        = number
    memory_size    = number
    source_path    = string
    environment_variables = map(string)
  }))
  default = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "dynamodb_table_arns" {
  description = "Map of DynamoDB table ARNs for Lambda permissions"
  type        = map(string)
  default     = {}
}

variable "secrets_arns" {
  description = "List of Secrets Manager ARNs that Lambda functions need access to"
  type        = list(string)
  default     = []
}

variable "eventbridge_bus_arn" {
  description = "EventBridge bus ARN for domain events (optional)"
  type        = string
  default     = ""
}