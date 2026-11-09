data "archive_file" "inventory_helpers" {
  type        = "zip"
  output_path = "${path.module}/.terraform/inventory-helpers.zip"
  source {
    content  = file("${path.module}/src/inventory/inventory.py")
    filename = "python/inventory.py"
  }
}

resource "aws_lambda_layer_version" "inventory_helpers" {
  layer_name               = "${local.name_prefix}-inventory-helpers"
  filename                 = data.archive_file.inventory_helpers.output_path
  source_code_hash         = data.archive_file.inventory_helpers.output_base64sha256
  compatible_runtimes      = ["python3.13"]
  compatible_architectures = ["arm64"]
}
