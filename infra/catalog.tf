resource "aws_dynamodb_table" "products" {
  name         = "${local.name_prefix}-products"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "slug"

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
    hash_key        = "catalog_status"
    range_key       = "catalog_sort"
  }

  point_in_time_recovery {
    enabled = true
  }
  server_side_encryption {
    enabled = true
  }
}
