# Project Configuration
project_name = "starchild"
environment  = "dev"
aws_region   = "us-east-1"

# Optional: Custom domain for SPA
# domain_name = "app.example.com"

# Lambda Functions Configuration
lambda_functions = {
  hello = {
    description     = "Hello World Lambda function"
    handler        = "lambda_function.lambda_handler"
    runtime        = "python3.13"
    timeout        = 30
    memory_size    = 128
    source_path    = "./src/lambda/hello"
    environment_variables = {
      ENVIRONMENT = "dev"
    }
  }
  users = {
    description     = "User management Lambda function"
    handler        = "lambda_function.lambda_handler"
    runtime        = "python3.13"
    timeout        = 30
    memory_size    = 256
    source_path    = "./src/lambda/users"
    environment_variables = {
      ENVIRONMENT = "dev"
      TABLE_NAME  = "users"
    }
  }
}

# API Gateway Methods Configuration
api_methods = [
  {
    resource_path   = "hello"
    http_method     = "GET"
    lambda_function = "hello"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "users"
    http_method     = "GET"
    lambda_function = "users"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "users"
    http_method     = "POST"
    lambda_function = "users"
    authorization   = "NONE"
    cors_enabled    = true
  }
]

# Common tags for all resources
tags = {
  Project     = "starchild"
  Environment = "dev"
  ManagedBy   = "terraform"
  Owner       = "development-team"
}