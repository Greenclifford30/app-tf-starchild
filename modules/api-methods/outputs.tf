output "api_resources" {
  description = "Created API Gateway resources"
  value = {
    for k, v in aws_api_gateway_resource.method_resources : k => {
      id        = v.id
      path_part = v.path_part
    }
  }
}

output "api_methods" {
  description = "Created API Gateway methods"
  value = {
    for k, v in aws_api_gateway_method.methods : k => {
      resource_id = v.resource_id
      http_method = v.http_method
    }
  }
}