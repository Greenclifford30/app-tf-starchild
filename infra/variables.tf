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
