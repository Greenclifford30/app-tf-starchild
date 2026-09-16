resource "aws_cognito_user_pool" "admins" {
  name = "${local.name_prefix}-admins"
  admin_create_user_config {
    allow_admin_create_user_only = true
  }
  username_attributes = ["email"]
  auto_verified_attributes = ["email"]
}

resource "aws_cognito_user_pool_client" "admins" {
  name         = "${local.name_prefix}-catalog-admin-client"
  user_pool_id = aws_cognito_user_pool.admins.id
  generate_secret = false
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}

resource "aws_cognito_user_group" "product_admins" {
  name         = "starchild-admin"
  user_pool_id = aws_cognito_user_pool.admins.id
}
