# Create resources for each API method path
resource "aws_api_gateway_resource" "method_resources" {
  for_each = {
    for method in var.api_methods :
    method.resource_path => method
    if method.resource_path != "/"
  }

  rest_api_id = var.api_gateway_id
  parent_id   = var.api_gateway_resource_id
  path_part   = each.value.resource_path
}

# Create methods for each API endpoint
resource "aws_api_gateway_method" "methods" {
  for_each = {
    for i, method in var.api_methods :
    "${method.resource_path}-${method.http_method}" => method
  }

  rest_api_id = var.api_gateway_id
  resource_id = each.value.resource_path == "/" ? var.api_gateway_resource_id : aws_api_gateway_resource.method_resources[each.value.resource_path].id
  
  http_method   = each.value.http_method
  authorization = each.value.authorization
}

# Create integrations for each method
resource "aws_api_gateway_integration" "lambda_integrations" {
  for_each = {
    for i, method in var.api_methods :
    "${method.resource_path}-${method.http_method}" => method
  }

  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_method.methods[each.key].resource_id
  http_method = aws_api_gateway_method.methods[each.key].http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = var.lambda_functions[each.value.lambda_function].invoke_arn
}

# Create method responses for CORS-enabled methods
resource "aws_api_gateway_method_response" "method_responses" {
  for_each = {
    for i, method in var.api_methods :
    "${method.resource_path}-${method.http_method}" => method
    if method.cors_enabled
  }

  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_method.methods[each.key].resource_id
  http_method = aws_api_gateway_method.methods[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Create CORS OPTIONS methods for enabled endpoints
resource "aws_api_gateway_method" "cors_methods" {
  for_each = {
    for i, method in var.api_methods :
    method.resource_path => method
    if method.cors_enabled
  }

  rest_api_id = var.api_gateway_id
  resource_id = each.value.resource_path == "/" ? var.api_gateway_resource_id : aws_api_gateway_resource.method_resources[each.value.resource_path].id
  
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# Create CORS integrations
resource "aws_api_gateway_integration" "cors_integrations" {
  for_each = {
    for i, method in var.api_methods :
    method.resource_path => method
    if method.cors_enabled
  }

  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_method.cors_methods[each.key].resource_id
  http_method = aws_api_gateway_method.cors_methods[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

# Create CORS method responses
resource "aws_api_gateway_method_response" "cors_method_responses" {
  for_each = {
    for i, method in var.api_methods :
    method.resource_path => method
    if method.cors_enabled
  }

  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_method.cors_methods[each.key].resource_id
  http_method = aws_api_gateway_method.cors_methods[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

# Create CORS integration responses
resource "aws_api_gateway_integration_response" "cors_integration_responses" {
  for_each = {
    for i, method in var.api_methods :
    method.resource_path => method
    if method.cors_enabled
  }

  rest_api_id = var.api_gateway_id
  resource_id = aws_api_gateway_method.cors_methods[each.key].resource_id
  http_method = aws_api_gateway_method.cors_methods[each.key].http_method
  status_code = aws_api_gateway_method_response.cors_method_responses[each.key].status_code
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS,POST,PUT,DELETE'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }

}