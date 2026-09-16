# Starchild MVP order backend

This Terraform root deploys the order-request backend and product catalog:

- API Gateway HTTP API (`POST /orders`)
- Lambda validation and price calculation
- DynamoDB durable order storage
- SNS email notifications
- CloudWatch logs
- DynamoDB-backed public product catalog and admin CRUD API
- Cognito admin identity, private S3 product media, and CloudFront delivery

Terraform is split by responsibility: `main.tf` contains provider configuration and shared locals; `orders.tf` contains orders/API Gateway; `catalog.tf` contains the product table; `products_api.tf` contains the product Lambda and routes; `media.tf` contains S3/CloudFront; and `identity.tf` contains Cognito administration.

## Deploy

Create an untracked `terraform.tfvars` from `terraform.tfvars.example`. Set the order-notification email and the exact Amplify/custom-domain origins, then run:

```bash
terraform init
terraform fmt -check -recursive
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

Run the Lambda unit tests before planning:

```bash
python3 -m unittest discover -s tests -v
```

After `apply`:

1. Confirm the subscription email from Amazon SNS. Notifications are not delivered before confirmation.
2. Copy `orders_api_url` into `NEXT_PUBLIC_ORDERS_API_URL` and `products_api_url` into `PRODUCTS_API_URL` in Amplify.
3. Create a Cognito user, add it to the `starchild-admin` group, and authenticate against the output user pool/client before calling protected catalog routes.
4. Seed the checked-in seven-product catalog and its images:

   ```bash
   python3 scripts/bootstrap_products.py \
     --table "$(terraform output -raw products_table_name)" \
     --bucket "$(terraform output -raw product_media_bucket_name)" \
     --manifest data/initial-products.json \
     --media-dir ../web/starchild/public/products
   ```
5. Redeploy the Amplify branch so SSR has the catalog API environment variable.
6. Submit a real test order and verify both the DynamoDB item and notification email.

## Product API

`GET /products` and `GET /products/{slug}` are public. Cognito access tokens from a member of `starchild-admin` are required for `GET /admin/products`, `POST /products`, `PUT /products/{slug}`, `DELETE /products/{slug}`, and `POST /product-images/upload-url`.

Products use `priceCents` rather than a decimal price. `DELETE` archives a product, so it disappears from public catalog reads and cannot be ordered. Image upload requests accept a MIME type and return a 15-minute presigned PUT URL; product writes reference the returned image key.

The notification address is intentionally supplied only through Terraform variables; it is not committed or exposed to the browser.
