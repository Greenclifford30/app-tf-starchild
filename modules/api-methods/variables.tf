variable "api_gateway_id" {
  description = "ID of the API Gateway"
  type        = string
}

variable "api_gateway_resource_id" {
  description = "Root resource ID of the API Gateway"
  type        = string
}

variable "lambda_functions" {
  description = "Map of Lambda function details"
  type = map(object({
    function_name = string
    function_arn  = string
    invoke_arn    = string
  }))
}

variable "api_methods" {
  description = "List of API Gateway methods to create"
  type = list(object({
    resource_path   = string
    http_method     = string
    lambda_function = string
    authorization   = string
    cors_enabled    = bool
  }))
  default = []
}