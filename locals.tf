locals {
    tables = {
        products   = "products"
        variants   = "variants"
        carts      = "carts"
        orders     = "orders"
        customers  = "customers"
        inventory  = "inventory"
    }

    # Secrets ARNs (create these in AWS Secrets Manager)
    secrets = {
        stripe_secret_arn         = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/${var.environment}/stripe-api-key"
        stripe_webhook_secret_arn = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.project_name}/${var.environment}/stripe-webhook-secret"
    }

    common_env = {
        ENVIRONMENT          = "dev"
        ALLOWED_ORIGINS      = "*"
        LOG_LEVEL            = "INFO"
        # Region can be set via Lambda execution env; include if you prefer explicitness
        AWS_REGION           = "us-east-1"
  }
}

# Data source for current AWS account ID
data "aws_caller_identity" "current" {}