variable "aws_region" {
  description = "AWS Region for the Starchild MVP backend."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to prefix MVP resources."
  type        = string
  default     = "starchild"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "notification_email" {
  description = "Private email address subscribed to order-request notifications."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.notification_email))
    error_message = "notification_email must be a valid email address."
  }
}

variable "notification_transport" {
  description = "Order email delivery method. Switch to ses after verifying the sender and recipient eligibility."
  type        = string
  default     = "sns"

  validation {
    condition     = contains(["sns", "ses"], var.notification_transport)
    error_message = "notification_transport must be sns or ses."
  }
}

variable "retain_sns_notifications" {
  description = "Keep the existing SNS topic and email subscription during SES cutover."
  type        = bool
  default     = true
}

variable "allowed_origins" {
  description = "Additional exact Amplify and local browser origins; the starchildclo.com origins are always included."
  type        = list(string)
  default     = ["http://localhost:3000"]

  validation {
    condition     = length(var.allowed_origins) > 0 && alltrue([for origin in var.allowed_origins : can(regex("^https?://", origin))])
    error_message = "allowed_origins must contain at least one HTTP or HTTPS origin."
  }
}

variable "tags" {
  description = "Tags applied to all supported resources."
  type        = map(string)
  default = {
    Project   = "starchild"
    ManagedBy = "terraform"
  }
}

variable "payment_instructions" {
  description = "Shared customer payment instructions included in order confirmations."
  type        = string
  validation {
    condition     = length(trimspace(var.payment_instructions)) > 0 && length(var.payment_instructions) <= 2000
    error_message = "Set payment_instructions to nonempty shared instructions of at most 2000 characters."
  }
}

variable "customer_ses_ready" {
  description = "Confirm SES sender and DKIM are verified and production sending is enabled in this region."
  type        = bool
  validation {
    condition     = var.customer_ses_ready
    error_message = "Verify the SES domain and DKIM and obtain production sending access before enabling customer emails; set customer_ses_ready to true after verification."
  }
}

variable "stripe_payments_enabled" {
  description = "Enable Stripe infrastructure after building the SDK layer and preparing account configuration."
  type        = bool
  default     = false
}

variable "stripe_apparel_tax_code" {
  description = "Stripe Tax code configured for the store's apparel."
  type        = string
  default     = ""
  validation {
    condition     = var.stripe_apparel_tax_code == "" || can(regex("^txcd_[0-9]+$", var.stripe_apparel_tax_code))
    error_message = "Set a Stripe apparel tax code when payments are enabled."
  }
}
