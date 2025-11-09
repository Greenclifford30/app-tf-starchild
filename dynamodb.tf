# ============================================================================
# DynamoDB Tables for Starchild E-commerce Application
# ============================================================================
# Best practices for low-traffic applications:
# - On-demand billing (PAY_PER_REQUEST) for unpredictable/low traffic
# - Point-in-time recovery (PITR) for data protection
# - Server-side encryption with AWS managed keys
# - TTL for automatic cleanup of temporary data
# - GSIs for common query patterns
# ============================================================================

# ----------------------------------------------------------------------------
# Products Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "products" {
  name         = "${var.project_name}-${var.environment}-${local.tables.products}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "product_id"

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # GSI for querying products by status (e.g., list all active products)
  global_secondary_index {
    name            = "status-created_at-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-products"
    Description = "Product catalog table"
  })
}

# ----------------------------------------------------------------------------
# Variants Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "variants" {
  name         = "${var.project_name}-${var.environment}-${local.tables.variants}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "variant_id"

  attribute {
    name = "variant_id"
    type = "S"
  }

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "sku"
    type = "S"
  }

  # GSI for querying all variants of a product
  global_secondary_index {
    name            = "product_id-index"
    hash_key        = "product_id"
    projection_type = "ALL"
  }

  # GSI for SKU lookups
  global_secondary_index {
    name            = "sku-index"
    hash_key        = "sku"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-variants"
    Description = "Product variants table (SKUs, sizes, colors, etc.)"
  })
}

# ----------------------------------------------------------------------------
# Carts Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "carts" {
  name         = "${var.project_name}-${var.environment}-${local.tables.carts}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cart_id"

  attribute {
    name = "cart_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  # GSI for querying carts by customer (optional, for logged-in users)
  global_secondary_index {
    name            = "customer_id-index"
    hash_key        = "customer_id"
    projection_type = "ALL"
  }

  # Enable TTL for automatic cleanup of abandoned carts
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-carts"
    Description = "Shopping carts table with TTL for abandoned cart cleanup"
  })
}

# ----------------------------------------------------------------------------
# Orders Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "orders" {
  name         = "${var.project_name}-${var.environment}-${local.tables.orders}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  # GSI for querying orders by customer (chronologically)
  global_secondary_index {
    name            = "customer_id-created_at-index"
    hash_key        = "customer_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  # GSI for querying orders by status (for admin/operations)
  global_secondary_index {
    name            = "status-created_at-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-orders"
    Description = "Orders table for completed purchases"
  })
}

# ----------------------------------------------------------------------------
# Customers Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "customers" {
  name         = "${var.project_name}-${var.environment}-${local.tables.customers}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  # GSI for email lookups (must be unique in application logic)
  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-customers"
    Description = "Customer profiles and account data"
  })
}

# ----------------------------------------------------------------------------
# Inventory Table
# ----------------------------------------------------------------------------
resource "aws_dynamodb_table" "inventory" {
  name         = "${var.project_name}-${var.environment}-${local.tables.inventory}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "variant_id"

  attribute {
    name = "variant_id"
    type = "S"
  }

  ttl {
    enabled        = false
    attribute_name = ""
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-inventory"
    Description = "Inventory tracking table for stock management"
  })
}

# ----------------------------------------------------------------------------
# Idempotency Table
# ----------------------------------------------------------------------------
# Used for idempotent request handling to prevent duplicate operations
resource "aws_dynamodb_table" "idempotency" {
  name         = "${var.project_name}-${var.environment}-idempotency"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "idempotency_key"

  attribute {
    name = "idempotency_key"
    type = "S"
  }

  # Enable TTL for automatic cleanup of old idempotency records
  ttl {
    enabled        = true
    attribute_name = "ttl"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(var.tags, {
    Name        = "${var.project_name}-${var.environment}-idempotency"
    Description = "Idempotency keys for preventing duplicate operations"
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "dynamodb_tables" {
  description = "DynamoDB table information"
  value = {
    products = {
      name = aws_dynamodb_table.products.name
      arn  = aws_dynamodb_table.products.arn
    }
    variants = {
      name = aws_dynamodb_table.variants.name
      arn  = aws_dynamodb_table.variants.arn
    }
    carts = {
      name = aws_dynamodb_table.carts.name
      arn  = aws_dynamodb_table.carts.arn
    }
    orders = {
      name = aws_dynamodb_table.orders.name
      arn  = aws_dynamodb_table.orders.arn
    }
    customers = {
      name = aws_dynamodb_table.customers.name
      arn  = aws_dynamodb_table.customers.arn
    }
    inventory = {
      name = aws_dynamodb_table.inventory.name
      arn  = aws_dynamodb_table.inventory.arn
    }
    idempotency = {
      name = aws_dynamodb_table.idempotency.name
      arn  = aws_dynamodb_table.idempotency.arn
    }
  }
}
