resource "aws_acm_certificate" "api" {
  domain_name       = "api.starchildclo.com"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# When a hosted zone is supplied, keep the validation record for ACM renewal.
resource "aws_route53_record" "api_certificate_validation" {
  count   = var.api_route53_zone_id == null ? 0 : 1
  zone_id = var.api_route53_zone_id
  name    = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_name
  type    = tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_type
  records = [tolist(aws_acm_certificate.api.domain_validation_options)[0].resource_record_value]
  ttl     = 300
}

resource "aws_acm_certificate_validation" "api" {
  count                   = var.enable_api_custom_domain ? 1 : 0
  certificate_arn         = aws_acm_certificate.api.arn
  validation_record_fqdns = var.api_route53_zone_id == null ? null : [aws_route53_record.api_certificate_validation[0].fqdn]
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

resource "aws_route53_record" "api" {
  count   = var.enable_api_custom_domain && var.api_route53_zone_id != null ? 1 : 0
  zone_id = var.api_route53_zone_id
  name    = aws_apigatewayv2_domain_name.api[0].domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.api[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }

  depends_on = [aws_apigatewayv2_api_mapping.api]
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
