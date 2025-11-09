# Project Configuration
project_name = "starchild"
environment  = "dev"
aws_region   = "us-east-1"

# Optional: Custom domain for SPA
# domain_name = "app.example.com"

# Lambda Functions Configuration
lambda_functions = {
  # Health
  health = {
    description  = "Health probe"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 5
    memory_size  = 128
    source_path  = "./src/lambda/health"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
    }
  }

  # Catalog (public)
  get_products = {
    description  = "List products"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/get_products"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      PRODUCTS_TABLE  = "starchild-dev-products"
      VARIANTS_TABLE  = "starchild-dev-variants"
    }
  }
  get_product_by_id = {
    description  = "Get product by ID"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_product_by_id"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      PRODUCTS_TABLE  = "starchild-dev-products"
      VARIANTS_TABLE  = "starchild-dev-variants"
    }
  }

  # Cart (public)
  create_cart = {
    description  = "Create cart"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/create_cart"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      PRODUCTS_TABLE    = "starchild-dev-products"
      VARIANTS_TABLE    = "starchild-dev-variants"
      CART_TTL_HOURS    = "72"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  get_cart = {
    description  = "Get cart"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_cart"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      CARTS_TABLE     = "starchild-dev-carts"
    }
  }
  update_cart = {
    description  = "Update cart (addresses/discounts)"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/update_cart"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  add_cart_item = {
    description  = "Add item to cart"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/add_cart_item"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      VARIANTS_TABLE    = "starchild-dev-variants"
      INVENTORY_TABLE   = "starchild-dev-inventory"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  update_cart_item = {
    description  = "Update cart item"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/update_cart_item"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      VARIANTS_TABLE    = "starchild-dev-variants"
      INVENTORY_TABLE   = "starchild-dev-inventory"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  remove_cart_item = {
    description  = "Remove cart item"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/remove_cart_item"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      CARTS_TABLE     = "starchild-dev-carts"
      INVENTORY_TABLE = "starchild-dev-inventory"
    }
  }

  # Shipping (public)
  get_shipping_rates = {
    description  = "Quote shipping rates for a cart"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_shipping_rates"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      CARTS_TABLE     = "starchild-dev-carts"
      SHIP_PROVIDER   = "stub"
    }
  }
  select_shipping_rate = {
    description  = "Select shipping rate on cart"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/select_shipping_rate"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }

  # Checkout
  create_checkout_session = {
    description  = "Create checkout session (server-side)"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 20
    memory_size  = 512
    source_path  = "./src/lambda/create_checkout_session"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      STRIPE_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:starchild/dev/stripe-api-key"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }

  # Payments
  create_payment_intent = {
    description  = "Create/confirm Stripe PaymentIntent"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 25
    memory_size  = 512
    source_path  = "./src/lambda/create_payment_intent"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CARTS_TABLE       = "starchild-dev-carts"
      STRIPE_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:starchild/dev/stripe-api-key"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  get_payment_intent = {
    description  = "Retrieve PaymentIntent"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_payment_intent"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      STRIPE_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:starchild/dev/stripe-api-key"
    }
  }
  webhook_payment = {
    description  = "Stripe webhook receiver"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 20
    memory_size  = 256
    source_path  = "./src/lambda/webhook_payment"
    environment_variables = {
      ENVIRONMENT               = "dev"
      ALLOWED_ORIGINS           = "*"
      LOG_LEVEL                 = "INFO"
      AWS_REGION                = "us-east-1"
      STRIPE_WEBHOOK_SECRET_ARN = "arn:aws:secretsmanager:us-east-1:ACCOUNT_ID:secret:starchild/dev/stripe-webhook-secret"
      CARTS_TABLE               = "starchild-dev-carts"
      ORDERS_TABLE              = "starchild-dev-orders"
      IDEMPOTENCY_TABLE         = "starchild-dev-idempotency"
      EVENTS_BUS_NAME           = "starchild-domain-events"
    }
  }

  # Orders (protected)
  get_orders = {
    description  = "List orders for current user"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/get_orders"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      ORDERS_TABLE    = "starchild-dev-orders"
      CUSTOMERS_TABLE = "starchild-dev-customers"
    }
  }
  create_order = {
    description  = "Create order from paid cart (server-side)"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 20
    memory_size  = 256
    source_path  = "./src/lambda/create_order"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      ORDERS_TABLE      = "starchild-dev-orders"
      CARTS_TABLE       = "starchild-dev-carts"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  get_order_by_id = {
    description  = "Get order by ID"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_order_by_id"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      ORDERS_TABLE    = "starchild-dev-orders"
    }
  }
  cancel_order = {
    description  = "Request order cancellation"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/cancel_order"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      ORDERS_TABLE      = "starchild-dev-orders"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }

  # Me (protected)
  get_profile = {
    description  = "Get current user profile"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/get_profile"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      CUSTOMERS_TABLE = "starchild-dev-customers"
    }
  }
  update_profile = {
    description  = "Update current user profile"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/update_profile"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      CUSTOMERS_TABLE   = "starchild-dev-customers"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }

  # Admin (optional, protected)
  admin_create_product = {
    description  = "Admin: create product"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 20
    memory_size  = 256
    source_path  = "./src/lambda/admin_create_product"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      PRODUCTS_TABLE    = "starchild-dev-products"
      VARIANTS_TABLE    = "starchild-dev-variants"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  admin_list_products = {
    description  = "Admin: list products (all statuses)"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 15
    memory_size  = 256
    source_path  = "./src/lambda/admin_list_products"
    environment_variables = {
      ENVIRONMENT     = "dev"
      ALLOWED_ORIGINS = "*"
      LOG_LEVEL       = "INFO"
      AWS_REGION      = "us-east-1"
      PRODUCTS_TABLE  = "starchild-dev-products"
      VARIANTS_TABLE  = "starchild-dev-variants"
    }
  }
  admin_update_product = {
    description  = "Admin: update product/variants"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 20
    memory_size  = 256
    source_path  = "./src/lambda/admin_update_product"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      PRODUCTS_TABLE    = "starchild-dev-products"
      VARIANTS_TABLE    = "starchild-dev-variants"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
    }
  }
  admin_inventory_adjust = {
    description  = "Admin: inventory adjustment (atomic)"
    handler      = "lambda_function.lambda_handler"
    runtime      = "python3.13"
    timeout      = 10
    memory_size  = 256
    source_path  = "./src/lambda/admin_inventory_adjust"
    environment_variables = {
      ENVIRONMENT       = "dev"
      ALLOWED_ORIGINS   = "*"
      LOG_LEVEL         = "INFO"
      AWS_REGION        = "us-east-1"
      INVENTORY_TABLE   = "starchild-dev-inventory"
      IDEMPOTENCY_TABLE = "starchild-dev-idempotency"
      EVENTS_BUS_NAME   = "starchild-domain-events"
    }
  }
}

# API Gateway Methods Configuration
api_methods = [
  # Health
  {
    resource_path   = "health"
    http_method     = "GET"
    lambda_function = "health"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Catalog (public)
  {
    resource_path   = "products"
    http_method     = "GET"
    lambda_function = "get_products"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "products/{id}"
    http_method     = "GET"
    lambda_function = "get_product_by_id"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Cart (guest or logged-in; still public endpoints)
  {
    resource_path   = "carts"
    http_method     = "POST"
    lambda_function = "create_cart"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}"
    http_method     = "GET"
    lambda_function = "get_cart"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}"
    http_method     = "PATCH"
    lambda_function = "update_cart"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}/items"
    http_method     = "POST"
    lambda_function = "add_cart_item"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}/items"
    http_method     = "PATCH"
    lambda_function = "update_cart_item"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}/items"
    http_method     = "DELETE"
    lambda_function = "remove_cart_item"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Shipping (public; requires address present on cart)
  {
    resource_path   = "carts/{cartId}/shipping-rates"
    http_method     = "GET"
    lambda_function = "get_shipping_rates"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "carts/{cartId}/shipping-rate"
    http_method     = "POST"
    lambda_function = "select_shipping_rate"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Checkout (server-side session creation)
  {
    resource_path   = "checkout/sessions"
    http_method     = "POST"
    lambda_function = "create_checkout_session"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Payments (server-side; public from API GW perspective, actual payment auth happens with provider)
  {
    resource_path   = "payments/intents"
    http_method     = "POST"
    lambda_function = "create_payment_intent"
    authorization   = "NONE"
    cors_enabled    = true
  },
  {
    resource_path   = "payments/intents/{intentId}"
    http_method     = "GET"
    lambda_function = "get_payment_intent"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Webhooks (must be unauthenticated at API GW; verify signature in Lambda)
  {
    resource_path   = "webhooks/payments"
    http_method     = "POST"
    lambda_function = "webhook_payment"
    authorization   = "NONE"
    cors_enabled    = true
  },

  # Orders (protected)
  {
    resource_path   = "orders"
    http_method     = "GET"
    lambda_function = "get_orders"
    authorization   = "JWT"
    cors_enabled    = true
  },
  {
    resource_path   = "orders"
    http_method     = "POST"
    lambda_function = "create_order"
    authorization   = "JWT"
    cors_enabled    = true
  },
  {
    resource_path   = "orders/{orderId}"
    http_method     = "GET"
    lambda_function = "get_order_by_id"
    authorization   = "JWT"
    cors_enabled    = true
  },
  {
    resource_path   = "orders/{orderId}/cancel"
    http_method     = "POST"
    lambda_function = "cancel_order"
    authorization   = "JWT"
    cors_enabled    = true
  },

  # Me (protected)
  {
    resource_path   = "me"
    http_method     = "GET"
    lambda_function = "get_profile"
    authorization   = "JWT"
    cors_enabled    = true
  },
  {
    resource_path   = "me"
    http_method     = "PATCH"
    lambda_function = "update_profile"
    authorization   = "JWT"
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