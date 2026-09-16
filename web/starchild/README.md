# Starchild storefront

Next.js storefront deployed through AWS Amplify Hosting. The catalog is server-rendered from the Terraform-managed products API; cart state is stored in the browser and order requests are submitted to the order API.

## Local development

Use Node.js 22 and create `.env.local`:

```bash
NEXT_PUBLIC_ORDERS_API_URL=https://example.execute-api.us-east-1.amazonaws.com/orders
PRODUCTS_API_URL=https://example.execute-api.us-east-1.amazonaws.com
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

The repository-level `amplify.yml` declares this directory as the monorepo application root. Configure `NEXT_PUBLIC_ORDERS_API_URL` and the server-only `PRODUCTS_API_URL` with the Terraform outputs before building the production branch. The storefront now requires Amplify SSR hosting so products created after deployment receive working detail routes.

Because `NEXT_PUBLIC_` variables are embedded into the client bundle at build time, changing the API URL requires a new Amplify deployment.
