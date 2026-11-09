resource "aws_acm_certificate" "api" {
  domain_name       = "api.starchildclo.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# DNS is managed outside this Terraform root. Enable the mapping only after
# publishing the certificate validation record exposed in the output.
resource "aws_acm_certificate_validation" "api" {
  count           = var.enable_api_custom_domain ? 1 : 0
  certificate_arn = aws_acm_certificate.api.arn
}

resource "aws_apigatewayv2_domain_name" "api" {
  count       = var.enable_api_custom_domain ? 1 : 0
  domain_name = aws_acm_certificate.api.domain_name

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.api[0].certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "api" {
  count       = var.enable_api_custom_domain ? 1 : 0
  api_id      = aws_apigatewayv2_api.orders.id
  domain_name = aws_apigatewayv2_domain_name.api[0].id
  stage       = aws_apigatewayv2_stage.default.id
}

output "api_certificate_validation_records" {
  description = "Publish these DNS records to validate and renew the API certificate."
  value = [for option in aws_acm_certificate.api.domain_validation_options : {
    name  = option.resource_record_name
    type  = option.resource_record_type
    value = option.resource_record_value
  }]
}

output "api_custom_domain_dns_record" {
  description = "Publish this CNAME at the DNS provider after enabling the API custom domain."
  value = var.enable_api_custom_domain ? {
    name  = aws_apigatewayv2_domain_name.api[0].domain_name
    type  = "CNAME"
    value = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
  } : null
}

output "api_custom_domain_url" {
  description = "Custom API base URL; use only after publishing and verifying its DNS record."
  value       = var.enable_api_custom_domain ? "https://${aws_apigatewayv2_domain_name.api[0].domain_name}" : null
}
