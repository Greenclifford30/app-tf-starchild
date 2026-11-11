# Starchild storefront

Next.js storefront deployed through AWS Amplify Hosting. The catalog is server-rendered from the Terraform-managed products API; cart state is stored in the browser and Stripe Checkout authorizes payment before the order is reviewed.

## Local development

Use Node.js 22 and create `.env.local`:

```bash
NEXT_PUBLIC_ORDERS_API_URL=https://example.execute-api.us-east-1.amazonaws.com/orders
NEXT_PUBLIC_PAYMENTS_API_URL=https://example.execute-api.us-east-1.amazonaws.com
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_example
PRODUCTS_API_URL=https://example.execute-api.us-east-1.amazonaws.com
COGNITO_USER_POOL_ID=us-east-1_example
COGNITO_USER_POOL_CLIENT_ID=exampleclientid
```

Then run:

```bash
npm ci
npm run dev
```

## Verification

```bash
npm run lint
npm run build
```

## Amplify

The repository-level `amplify.yml` declares this directory as the monorepo application root. Configure `NEXT_PUBLIC_PAYMENTS_API_URL`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_ORDERS_API_URL`, the server-only `PRODUCTS_API_URL`, `COGNITO_USER_POOL_ID`, and `COGNITO_USER_POOL_CLIENT_ID` with the Terraform outputs before building the production branch. The storefront now requires Amplify SSR hosting so products created after deployment receive working detail routes. The private catalog manager is available at `/admin` and signs in with a user in the `starchild-admin` Cognito group.

Because `NEXT_PUBLIC_` variables are embedded into the client bundle at build time, changing the API URL requires a new Amplify deployment.

## Order administration

Sign in at `/admin`, then choose **Requests & orders**. Stripe requests show the authorized total and hold expiry. Verify availability, then confirm and capture; Stripe events update the payment status. Declining releases the hold. Canceled paid Stripe orders support a full refund action. Earlier manual requests and orders retain their existing workflow. Stock is still checked manually and is not reserved. See the Stripe deployment and recovery instructions in `infra/README.md`.
