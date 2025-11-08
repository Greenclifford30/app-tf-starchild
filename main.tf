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
  
  tags = var.tags
}

# API Gateway Methods
module "api_methods" {
  source = "./modules/api-methods"
  
  api_gateway_id            = module.api_gateway.api_gateway_id
  api_gateway_resource_id   = module.api_gateway.api_gateway_root_resource_id
  lambda_functions          = module.lambda_functions.lambda_functions
  
  api_methods = var.api_methods
}