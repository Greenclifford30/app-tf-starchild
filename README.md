# Starchild Clothing MVP

Starchild is a Next.js storefront for browsing products, selecting variants, maintaining a persistent cart, and submitting a manual order request. No online payment is collected in the MVP.

## Architecture

```text
AWS Amplify Hosting (Next.js)
          |
          | POST /orders
          v
API Gateway HTTP API -> Lambda -> DynamoDB
                                  |
                                  v
                              SNS email
```

- `web/starchild`: Next.js frontend hosted by AWS Amplify
- `infra`: Terraform-managed order API and notification backend
- `amplify.yml`: Amplify monorepo build configuration
- `STARCHILD_MVP_LAUNCH_PLAN.md`: launch checklist and production QA gate

## Local verification

Frontend:

```bash
cd web/starchild
npm ci
npm run lint
npm run build
```

Backend:

```bash
cd infra
python3 -m unittest discover -s tests -v
terraform init
terraform fmt -check -recursive
terraform validate
```

See the README files in `web/starchild` and `infra` for environment and deployment instructions.
