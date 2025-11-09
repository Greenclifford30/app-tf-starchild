terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# API Gateway
module "api_gateway" {
  source = "./modules/api-gateway"
  
  project_name = var.project_name
  environment  = var.environment
  
  tags = var.tags
}

# Lambda Functions
module "lambda_functions" {
  source = "./modules/lambda"

  project_name     = var.project_name
  environment      = var.environment
  api_gateway_id   = module.api_gateway.api_gateway_id
  api_gateway_execution_arn = module.api_gateway.api_gateway_execution_arn

  functions = var.lambda_functions

  # DynamoDB table ARNs for IAM permissions
  dynamodb_table_arns = {
    products    = aws_dynamodb_table.products.arn
    variants    = aws_dynamodb_table.variants.arn
    carts       = aws_dynamodb_table.carts.arn
    orders      = aws_dynamodb_table.orders.arn
    customers   = aws_dynamodb_table.customers.arn
    inventory   = aws_dynamodb_table.inventory.arn
    idempotency = aws_dynamodb_table.idempotency.arn
  }

  # Secrets Manager ARNs for Stripe credentials
  secrets_arns = [
    "${local.secrets.stripe_secret_arn}*",
    "${local.secrets.stripe_webhook_secret_arn}*"
  ]

  # EventBridge bus ARN (optional - create this resource if needed)
  # eventbridge_bus_arn = aws_cloudwatch_event_bus.domain_events.arn

  tags = var.tags

  depends_on = [
    aws_dynamodb_table.products,
    aws_dynamodb_table.variants,
    aws_dynamodb_table.carts,
    aws_dynamodb_table.orders,
    aws_dynamodb_table.customers,
    aws_dynamodb_table.inventory,
    aws_dynamodb_table.idempotency
  ]
}

# API Gateway Methods
module "api_methods" {
  source = "./modules/api-methods"
  
  api_gateway_id            = module.api_gateway.api_gateway_id
  api_gateway_resource_id   = module.api_gateway.api_gateway_root_resource_id
  lambda_functions          = module.lambda_functions.lambda_functions
  
  api_methods = var.api_methods
}