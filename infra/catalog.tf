resource "aws_dynamodb_table" "products" {
  name         = "${local.name_prefix}-products"
  billing_mode = "PAY_PER_REQUEST"

  key_schema {
    attribute_name = "slug"
    key_type       = "HASH"
  }

  attribute {
    name = "slug"
    type = "S"
  }
  attribute {
    name = "catalog_status"
    type = "S"
  }
  attribute {
    name = "catalog_sort"
    type = "S"
  }

  global_secondary_index {
    name            = "catalog"
    projection_type = "ALL"

    key_schema {
      attribute_name = "catalog_status"
      key_type       = "HASH"
    }

    key_schema {
      attribute_name = "catalog_sort"
      key_type       = "RANGE"
    }
  }

  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}
