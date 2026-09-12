# Starchild MVP order backend

This Terraform root deploys only the backend required for the order-request MVP:

- API Gateway HTTP API (`POST /orders`)
- Lambda validation and price calculation
- DynamoDB durable order storage
- SNS email notifications
- CloudWatch logs

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
2. Copy the `orders_api_url` output into the Amplify environment variable `NEXT_PUBLIC_ORDERS_API_URL`.
3. Redeploy the Amplify branch because `NEXT_PUBLIC_` values are embedded during the Next.js build.
4. Submit a real test order and verify both the DynamoDB item and notification email.

The notification address is intentionally supplied only through Terraform variables; it is not committed or exposed to the browser.
