# Starchild MVP order backend

This Terraform root deploys the order-request backend and product catalog:

- API Gateway HTTP API (`POST /orders`)
- Lambda validation and price calculation
- DynamoDB durable order storage
- Operator order notifications through SNS or Amazon SES
- CloudWatch logs
- DynamoDB-backed public product catalog and admin CRUD API
- Cognito admin identity, private S3 product media, and CloudFront delivery

Terraform is split by responsibility: `main.tf` contains provider configuration and shared locals; `orders.tf` contains orders/API Gateway; `catalog.tf` contains the product table; `products_api.tf` contains the product Lambda and routes; `media.tf` contains S3/CloudFront; and `identity.tf` contains Cognito administration.

## Deploy

Create an untracked `terraform.tfvars` from `terraform.tfvars.example`. Set the order-notification email and any additional exact browser origins.

The API, Lambda handlers, and product-media bucket always allow `https://starchildclo.com` and `https://www.starchildclo.com`. Use `allowed_origins` for additional exact origins, such as the deployed Amplify hostname and local development; existing entries are retained alongside the custom domains.

Then run:

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

1. While using SNS, confirm the subscription email from Amazon SNS. Notifications are not delivered before confirmation. See the SES cutover below for branded sender setup.
2. In Amplify, set `NEXT_PUBLIC_ORDERS_API_URL` from `orders_api_url`, `PRODUCTS_API_URL` from `products_api_url`, `COGNITO_USER_POOL_ID` from `product_admin_user_pool_id`, and `COGNITO_USER_POOL_CLIENT_ID` from `product_admin_client_id`.
3. Create a Cognito user, add it to the `starchild-admin` group, and authenticate against the output user pool/client before calling protected catalog routes.
4. Seed the checked-in seven-product catalog and its images:

   ```bash
   python3 scripts/bootstrap_products.py \
     --table "$(terraform output -raw products_table_name)" \
     --bucket "$(terraform output -raw product_media_bucket_name)" \
     --manifest data/initial-products.json \
     --media-dir ../web/starchild/public/products
   ```
5. Redeploy the Amplify branch so SSR has the catalog API and administrator sign-in environment variables.
6. Submit a real test order and verify both the DynamoDB item and notification email.

## Product API

`GET /products` and `GET /products/{slug}` are public. Cognito ID tokens from a member of `starchild-admin` are required for `GET /admin/products`, `POST /products`, `PUT /products/{slug}`, `DELETE /products/{slug}`, and `POST /product-images/upload-url`.

Products use `priceCents` rather than a decimal price. `DELETE` archives a product, so it disappears from public catalog reads and cannot be ordered. Image upload requests accept a MIME type and return a 15-minute presigned PUT URL; product writes reference the returned image key.

The notification address is intentionally supplied only through Terraform variables; it is not committed or exposed to the browser.

## Branded order email cutover

The existing SNS subscription remains the default during setup. Amazon SES sends the same order alert from `Starchild <orders@starchildclo.com>` after the following staged cutover. This does not change Cognito account emails.

1. Keep `notification_transport = "sns"` and `retain_sns_notifications = true`, then apply Terraform. Existing SNS resources are retained; Terraform's moved blocks preserve their state addresses.
2. Run `terraform output -json notification_ses_dns_records` and add each TXT and CNAME record to the DNS provider for `starchildclo.com`. Use the record names as required by the DNS provider (some automatically append the domain). Wait until the domain identity and DKIM both show verified in Amazon SES in the configured AWS region.
3. Check the SES account's sending status in that region. In the SES sandbox, verify the existing `notification_email` recipient as well; alternatively, obtain SES production access before sending to an unverified recipient. Confirm sending is enabled and the domain identity is verified.
4. Set `notification_transport = "ses"` while keeping `retain_sns_notifications = true`, review and apply the Terraform plan, and submit a real test order. Confirm the operator receives the message from Starchild with the expected order details and that the request is stored. SES acceptance does not guarantee inbox delivery; check spam and SES sending status if necessary.
5. After the test succeeds, set `retain_sns_notifications = false`, review the plan for removal of the SNS subscription and topic, and apply. To roll back before removing SNS, set the transport back to `sns` and apply. If SNS was already removed, restore it and confirm the new subscription before switching back.

If SES rejects a send, the request remains saved and the customer receives a retry message. A retry attempts delivery again. A send accepted by SES followed by a failure recording its status can result in a duplicate on retry; the status indicates acceptance by SES, not inbox delivery.

## Confirmed order management

The existing `POST /orders` continues to create requests. Administrators use the existing Cognito ID-token authorizer and the `starchild-admin` group to review requests and manage confirmed orders at `/admin/orders`. The frontend proxies administration calls using the existing server-only `PRODUCTS_API_URL`; no new frontend environment variables are required. API Gateway validates the JWT and the order Lambda verifies the group and actor claim.

### Data model and access patterns

- The existing request table is keyed by `submission_id`. Its `review` GSI uses `review_status` (`PENDING`, `CONVERTED`, `DECLINED`) and `review_sort` (`created_at#submission_id`) for paginated review. A converted request stores `order_id`; a declined request stores its reason and reviewer.
- The new `confirmed-orders` table uses `pk` and `sk`. An order is `ORDER#{id}` / `META`; events are `ORDER#{id}` / `EVENT#{timestamp}#{eventId}`; action deduplication uses `ORDER#{id}` / `OP#{operationId}`; number reservations are `NUMBER#{number}` / `RESERVED`.
- The `all-orders`, `by-status`, and sparse `by-fulfillment` GSIs use `all_pk`, `status_pk`, and `fulfillment_pk` respectively, with `index_sort` (`created_at#orderId`). They project list summaries rather than item or contact details. Request linkage gives direct request-to-order lookup; customer order history is deferred.
- GSIs are eventually consistent. Detail reads use the primary table with strong consistency. The table is on-demand, encrypted, and has point-in-time recovery enabled.
- Confirmation transactionally verifies current catalog fields, links the request, reserves the order number, and creates the order and confirmation event. Each later action transactionally checks the version, updates the order, and records the event and operation ID. Retrying a completed operation is safe beyond DynamoDB's transaction-token window.

### API contract

All routes below require a valid token from the existing user pool and `starchild-admin`. They return JSON, use bounded `limit` (1–50) and opaque `cursor` query parameters for lists, and return `nextCursor` when another page is available.

| Route | Contract |
| --- | --- |
| `GET /admin/order-requests?status=PENDING` | List requests by `PENDING`, `CONVERTED`, or `DECLINED` review status. |
| `GET /admin/order-requests/{id}` | Request plus `preview` with current item snapshots, subtotal and `quoteToken`; `previewError` explains unavailable products. |
| `POST /admin/order-requests/{id}/confirm` | `quoteToken`, `availabilityConfirmed`, `fulfillmentMethod`, `pickupInstructions`, integer `discountCents`, `shippingCents`, `taxCents`, and `adjustmentReason`. Returns the confirmed order. |
| `POST /admin/order-requests/{id}/decline` | Required `reason`; returns the preserved request. |
| `GET /admin/orders` | List all orders; filter with `status=CONFIRMED|PROCESSING|COMPLETED|CANCELED` or `fulfillment=open`. |
| `GET /admin/orders/{id}` | Retrieve the complete order. |
| `GET /admin/orders/{id}/events` | List order events, newest first. |
| `POST /admin/orders/{id}/actions` | `action`, current integer `version`, UUID `operationId`, plus action-specific fields; returns the updated order. |

Actions are `START_PROCESSING`, `RECORD_PAYMENT` (`paymentMethod`, optional `paymentReference`), `SHIP` (`carrier`, optional `tracking`), `DELIVER`, `READY_FOR_PICKUP`, `PICK_UP`, `PICKED_UP_AND_PAY` (payment fields), and `CANCEL` (`reason`). Payment must be recorded before shipment or pickup. Payment is the full order total. A paid cancellation before handoff keeps the payment marked paid and flags external refund follow-up; this release does not record refunds. Completion and cancellation close the order. Availability is manually checked, not reserved.

### Deployment and backfill

1. Run backend tests, frontend lint/build, and `terraform fmt -check -recursive` / `terraform validate`. Review and apply an additive Terraform plan; wait for all GSIs to become active before using the new screens. Preserve the existing request-table Terraform output: `orders_table_name` still identifies that table. `confirmed_orders_table_name` identifies the new table.
2. Run the backfill with AWS credentials able to scan and update the request table:

   ```bash
   python3 scripts/backfill_order_requests.py \
     --table "$(terraform output -raw orders_table_name)" \
     --checkpoint /tmp/starchild-request-backfill.json
   ```

   The script resumes at the last completed page and uses conditional updates, so rerunning is safe and does not overwrite a concurrent review. Keep the checkpoint private. New requests are indexed automatically.
3. Deploy the frontend and verify that an admin can review a request, confirm it, record payment, fulfill a test order, and inspect its history. Verify an unauthenticated user and a user outside the admin group cannot access the API. Submit and retry a public order request and verify the existing notification flow.
4. If rollout must be paused, keep both tables and their indexes, disable the new admin routes/screens, and preserve confirmed orders. Do not delete the request or confirmed-order data.

No stock counts are inferred. A future inventory phase should model stable size/color variants and available/reserved counts in the existing products table, use transactional conditional reservation and release, and change catalog writes so they cannot overwrite inventory fields. Future hosted checkout must verify provider events server-side and add reconciliation, idempotency, and refund handling; card data must never be stored here.
