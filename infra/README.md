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

## API custom domain

The API can also be reached at `https://api.starchildclo.com`. DNS for the domain is managed outside this Terraform root. Deploy this configuration only in the AWS account and region that own the existing production API; the regional ACM certificate and API Gateway domain must be in the same region as the API. If the hostname or certificate is already managed elsewhere, reconcile or import those resources before applying.

1. Leave `enable_api_custom_domain = false` and apply the plan to request the ACM certificate. Run `terraform output -json api_certificate_validation_records` and publish the returned CNAME at the authoritative DNS provider. Some providers append `starchildclo.com` automatically; enter the name in their expected format. Keep this record in place for certificate renewal.
2. Once the record is publicly resolvable, set `enable_api_custom_domain = true` in the private Terraform variables and apply. Terraform waits for ACM validation, then creates the regional API Gateway custom domain and maps the existing `$default` stage to its root. Validation can take time; check the record if the apply times out.
3. Run `terraform output -json api_custom_domain_dns_record` and publish the returned CNAME for `api.starchildclo.com`. Wait for DNS propagation and verify `https://api.starchildclo.com/products` and the existing authenticated and order routes. Do not remove the original API Gateway endpoint.
4. After verification, set Amplify's `PRODUCTS_API_URL`, `NEXT_PUBLIC_PAYMENTS_API_URL`, and `NEXT_PUBLIC_ORDERS_API_URL` from their Terraform outputs, then redeploy the branch. When the custom domain is enabled, these outputs use it; otherwise, they use the API Gateway endpoint.

If Stripe is enabled, the existing webhook can continue using its original URL. To move it, configure and verify `https://api.starchildclo.com/stripe/webhook` in Stripe, including its signing secret and event delivery, before retiring the old endpoint. Changing the hostname alone does not update Amplify or Stripe.

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

For legacy manual orders, actions are `START_PROCESSING`, `RECORD_PAYMENT` (`paymentMethod`, optional `paymentReference`), `SHIP` (`carrier`, optional `tracking`), `DELIVER`, `READY_FOR_PICKUP`, `PICK_UP`, `PICKED_UP_AND_PAY` (payment fields), and `CANCEL` (`reason`). Payment must be recorded before shipment or pickup. Payment is the full order total. A paid manual cancellation before handoff keeps the payment marked paid and flags external refund follow-up. Stripe refunds use the separate workflow below. Completion and cancellation close the order. Availability is manually checked, not reserved.

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

No stock counts are inferred. The `manual_order_inventory_enabled` setting defaults to false. When enabled, confirmation of a manual request reserves its counted variants; shipment or pickup consumes that reservation, and cancellation releases it. Existing orders without a reservation do not change stock. Keep the setting disabled until the Stripe checkout reservation lifecycle is implemented: Stripe checkouts and earlier Stripe requests still do not reserve stock. Continue verifying availability manually for all requests. Stripe checkout uses server-verified provider events and idempotent operations as described below; card data is not stored here.

## Customer order emails

Customer emails use SES independently of the operator's SNS/SES setting. Before applying this release, verify the SES sending domain and DKIM in the configured region, obtain SES production access (the sandbox cannot send to arbitrary customers), and confirm sending is enabled. Follow the DNS steps above; verification and production access must already be complete. Set `customer_ses_ready = true` only after these checks and set `payment_instructions` in the private Terraform variables to the shared instructions customers should receive. Terraform requires both values; the readiness value is an operator attestation, not an automated SES status check. Payment instructions are stored in Terraform state, the Lambda configuration, and notification snapshots, so do not put secrets in them. Confirm the separate customer-notification alarm SNS subscription sent to `notification_email`.

New requests and administrator transitions atomically create customer email jobs in the `customer-notifications` DynamoDB table. A stream-triggered Lambda sends them through SES and records `SENT` or `FAILED`, the SES message ID, and failure attempts. Retries are automatic; after five retries the stream failure is placed on the encrypted failure queue and the CloudWatch alarm emails the operator. `SENT` means SES accepted the message, not inbox delivery; SES acceptance followed by a failure updating the job can result in a duplicate. Email changes do not roll back an order transition. Existing operator alert behavior remains separate.

For an alarm, inspect the Lambda logs and scan the customer-notifications table for `status = FAILED`; the queue contains stream failure metadata, not the message body. Resolve the SES or configuration issue, then requeue each failed job by conditionally changing its status to `PENDING` (this triggers the stream again):

```bash
aws dynamodb update-item --table-name "$(terraform output -raw customer_notifications_table_name)" \
  --key '{"notification_id":{"S":"REPLACE_WITH_NOTIFICATION_ID"}}' \
  --update-expression 'SET #s = :pending' --condition-expression '#s = :failed' \
  --expression-attribute-names '{"#s":"status"}' \
  --expression-attribute-values '{":pending":{"S":"PENDING"},":failed":{"S":"FAILED"}}'
```

Verify the job becomes `SENT`, then remove the resolved failure metadata from the SQS queue so the alarm can clear. Outbox records and logs contain customer/order data; restrict access and follow the store's retention policy. Existing orders are not emailed retroactively. After deployment, submit a real request using a controlled customer address, confirm operator and customer receipt, and exercise confirmation, payment and both shipping and pickup updates. Check the outbox, alarm subscription, logs and SES sending status. A test to a verified address in the SES sandbox does not establish readiness to email arbitrary customers.

## Stripe authorization checkout

Stripe is disabled in Terraform by default. The storefront build requires the Stripe public settings, so deploy the backend and configure the account before deploying the new storefront. Existing manual requests and orders keep their original workflow. New storefront orders are shipping-only, priced in USD, and use Stripe Tax with one store-wide apparel tax code. Stock is checked manually; holds do not reserve inventory.

1. The Stripe dependency layer is the versioned `artifacts/stripe-python-3.13-arm64.zip` file in this repository. Terraform Cloud receives it with the configuration; remote plan and apply need no build step. Terraform archives the shared Stripe and order-validation helpers directly from source into a separate layer. Commit the ZIP together with Terraform and helper changes so VCS-driven runs receive all required files.

   To update dependencies, edit the pinned `requirements-payments.txt`, run `./scripts/build_payment_layer.sh` from `infra` on a machine with Python/pip and package registry access, run the tests, and commit the resulting ZIP and requirements. The script builds for Linux arm64 and Python 3.13; ordinary helper edits do not require rebuilding the ZIP.
2. Configure `stripe_payments_enabled = true` and `stripe_apparel_tax_code` in private Terraform variables. Review and apply the infrastructure plan. Terraform creates a Secrets Manager secret container but never stores Stripe secret values in state.
3. Create a Stripe webhook endpoint for `stripe_webhook_url`, pinned to API version `2026-10-28.endive`, listening for `checkout.session.completed`, `checkout.session.expired`, `payment_intent.succeeded`, `payment_intent.canceled`, `payment_intent.payment_failed`, `refund.created`, `refund.updated`, and `refund.failed`. Stripe retries rejected events; use the Stripe dashboard to inspect and resend failed deliveries.
4. In AWS Secrets Manager, provision the secret identified by `stripe_secret_arn` as a JSON object with `secret_key` and `webhook_secret` string properties. Use a Stripe test secret key and the endpoint’s test signing secret for test deployments. Keep test and live environments separate.
5. Verify Stripe Tax registrations and the store-wide tax code. In Stripe Dashboard payment method settings for each test and live environment, enable cards, Apple Pay, and Google Pay, and disable other payment methods for this Checkout flow; the authorization and expiry handling currently supports card-based payments only. Register every checkout domain (including `starchildclo.com`, `www.starchildclo.com`, and any test domains) in Stripe payment method domains. Apple Pay and Google Pay appear only when the account, domain, browser, and customer device are eligible.
6. Set `NEXT_PUBLIC_PAYMENTS_API_URL` to `payments_api_url` and `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` to the corresponding Stripe publishable key in Amplify. Deploy the frontend. Test with Stripe test cards, eligible wallet devices over HTTPS, an address with configured tax, and a controlled customer email. Verify the authorization, admin capture, webhook-driven paid status, cancellation, and full refund.

Each checkout attempt stores the catalog item and shipping snapshot before creating a Stripe Session. The idempotency key binds it to the bag. Only a verified completed-session event with a capturable PaymentIntent and matching totals creates an admin review request. The customer sees a hold until capture; the admin cannot alter the Stripe total or manually record a Stripe payment. Confirmation links an order before capture, so a timeout leaves a pending order that can be safely retried from the admin. Webhook updates are conditional and can be retried. A canceled hold or failed capture needs a new customer checkout. A failed refund is flagged for operator follow-up; do not issue another automatic refund without investigating it in Stripe.

A scheduled job alerts the existing notification-alert SNS topic when holds have waited 48 hours or expire within 24 hours, and reconciles expired holds. The API and Lambda error alarms use the same topic. Confirm the topic subscription and monitor Stripe webhook delivery; the application does not guarantee availability or reserve stock. Stripe may release a hold before review, so review the actual expiry shown in admin. Keep the payment Lambda, layer, secrets, order tables, and webhook endpoint in place while any holds or refunds remain unresolved.
