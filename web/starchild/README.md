# Starchild storefront

Next.js storefront deployed through AWS Amplify Hosting. Product data is static for the MVP; cart state is stored in the browser and order requests are submitted to the Terraform-managed AWS order API.

## Local development

Use Node.js 22 and create `.env.local`:

```bash
NEXT_PUBLIC_ORDERS_API_URL=https://example.execute-api.us-east-1.amazonaws.com/orders
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

The repository-level `amplify.yml` declares this directory as the monorepo application root. Configure `NEXT_PUBLIC_ORDERS_API_URL` with the `infra` Terraform output before building the production branch.

Because `NEXT_PUBLIC_` variables are embedded into the client bundle at build time, changing the API URL requires a new Amplify deployment.
