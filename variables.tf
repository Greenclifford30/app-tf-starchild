variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "starchild"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "domain_name" {
  description = "Domain name for the SPA (optional)"
  type        = string
  default     = null
}

variable "lambda_functions" {
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

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "starchild"
    ManagedBy   = "terraform"
  }
}