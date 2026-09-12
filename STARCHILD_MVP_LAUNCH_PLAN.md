# Starchild Clothing MVP Launch Plan

## Goal

Ship a working Starchild Clothing MVP today.

A customer should be able to:

**Discover → Browse → Select variants → Add to cart → Submit an order request → Receive confirmation**

Starchild should receive enough information to manually confirm and fulfill the order.

---

## Current Launch Status — September 12, 2026

The MVP implementation is code-complete through the production build:

- Persistent variant-aware cart and real checkout summary
- Server-validated order-request Lambda with idempotent retries
- DynamoDB order storage and SNS operator notification
- Terraform-managed API Gateway, Lambda, DynamoDB, SNS, IAM, and logs
- Amplify monorepo build configuration
- Passing frontend lint, TypeScript, production build, Terraform validation, and Lambda tests

Remaining launch gates:

1. Create the Amplify application and record its production origin.
2. Supply the notification email and allowed origins through an untracked Terraform variable file.
3. Run `terraform plan` and `terraform apply` with authenticated AWS access.
4. Confirm the SNS email subscription.
5. Set `NEXT_PUBLIC_ORDERS_API_URL` in Amplify and deploy the frontend.
6. Submit and receive a real mobile test order from the production site.

---

## Working Method

Use a **40-minute focus / 10-minute break** Pomodoro cadence.

After every 3 focus sessions, take a **30–45 minute long break**.

### Rules for the day

- Each Pomodoro gets **one primary objective**.
- Do not chase unrelated improvements during a focus block.
- New ideas go into `POST-MVP.md` or the parking lot at the bottom of this file.
- Prioritize:
  - **P0** — Required to launch today
  - **P1** — Strongly recommended if time allows
  - **P2** — Post-MVP
- Once deployment begins, any new feature idea defaults to **P2** unless it prevents a customer from placing an order.
- At the end of each focus block, leave a one-line handoff note:
  - `NEXT: ...`

---

# MVP Scope

## P0 — Must Launch Today

- [x] Homepage/storefront works
- [x] Static product catalog is centralized and typed
- [x] Product detail pages work
- [x] Product URLs use clean slugs
- [x] Product images display correctly
- [x] Product size/color variants work
- [x] Add to cart works
- [x] Cart distinguishes product variants correctly
- [x] Cart quantity updates work
- [x] Remove from cart works
- [x] Cart subtotal is correct
- [x] Cart persists across refreshes
- [x] Checkout/order request form works
- [x] Customer information is validated
- [x] Order summary is shown before submission
- [x] No payment is collected online
- [ ] Order request reaches Starchild reliably
- [x] Customer sees a success/confirmation state
- [x] Production build passes
- [ ] Site is deployed
- [ ] HTTPS/domain work
- [ ] Full purchase flow passes on mobile

## P1 — Strongly Recommended Today

- [ ] Shipping page
- [ ] Returns/exchanges page
- [ ] Contact page
- [ ] Privacy policy
- [ ] Terms
- [x] Metadata/title/description
- [ ] OpenGraph metadata
- [x] Favicon
- [ ] Sitemap
- [ ] `robots.txt`
- [ ] Accessibility cleanup
- [ ] Responsive cleanup
- [ ] Image optimization
- [ ] Basic analytics

## P2 — Post-MVP

- [ ] Payments
- [ ] Customer accounts
- [ ] Database-backed product catalog
- [ ] Database-backed orders
- [ ] Admin portal
- [ ] Inventory management
- [ ] Shipping automation
- [ ] CMS
- [ ] Order history
- [ ] Automated transactional email workflows
- [ ] Discount codes
- [ ] Advanced analytics
- [ ] Authentication

---

# Pomodoro Schedule

## Pomodoro 1 — Repository Audit

### Objective

Understand the existing codebase before making changes.

### Tasks

- [ ] Review Next.js version and architecture
- [ ] Review App Router structure
- [ ] Identify mocked/incomplete functionality
- [ ] Review product data structure
- [ ] Review cart implementation
- [ ] Review state management
- [ ] Review image handling
- [ ] Review forms
- [ ] Review server/client component boundaries
- [ ] Identify build/type/lint issues
- [ ] Identify deployment constraints
- [ ] Categorize findings as P0/P1/P2

### Done when

There is a clear prioritized implementation plan and no uncertainty about the major launch blockers.

**NEXT:** ______________________________________

---

## Break — 10 minutes

Get away from the code.

- Water
- Stretch
- Walk
- Snack
- No feature planning

---

## Pomodoro 2 — Product Catalog

### Objective

Turn static/mock product information into a production-ready catalog structure.

### Tasks

- [ ] Create or confirm strongly typed `Product` model
- [ ] Centralize product data
- [ ] Add stable IDs
- [ ] Add slugs
- [ ] Add names/descriptions/prices
- [ ] Add product images
- [ ] Add available sizes
- [ ] Add available colors
- [ ] Add category
- [ ] Add featured status
- [ ] Add availability status
- [ ] Remove product definitions from UI components

### Done when

The storefront can render all current products from one consistent data source.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 3 — Product Experience

### Objective

Make browsing and selecting a product feel complete.

### Tasks

- [ ] Implement/verify product detail pages
- [ ] Use slug-based URLs
- [ ] Display all relevant product information
- [ ] Display product images cleanly
- [ ] Implement size selection
- [ ] Implement color selection
- [ ] Prevent invalid add-to-cart states
- [ ] Verify mobile product layout
- [ ] Verify navigation back to catalog

### Done when

A customer can confidently select the exact product variant they want.

**NEXT:** ______________________________________

---

# Long Break — 30–45 minutes

Take lunch or fully leave the desk.

Do not use the break to troubleshoot.

---

## Pomodoro 4 — Cart Core

### Objective

Replace mocked cart behavior with reliable client-side functionality.

### Tasks

- [ ] Add item
- [ ] Remove item
- [ ] Update quantity
- [ ] Prevent invalid quantities
- [ ] Calculate subtotal correctly
- [ ] Show cart item count
- [ ] Support multiple products
- [ ] Distinguish variants

Variant identity should treat these as different cart items:

- Same shirt / Black / Small
- Same shirt / Black / Large

### Done when

The cart behaves correctly during a normal session.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 5 — Cart Persistence + UX

### Objective

Make the cart survive refreshes and behave well on mobile.

### Tasks

- [ ] Persist cart to `localStorage`
- [ ] Restore cart after refresh
- [ ] Avoid hydration errors
- [ ] Handle empty-cart state
- [ ] Add clear-cart behavior
- [ ] Verify mobile cart layout
- [ ] Verify cart totals after reload
- [ ] Verify variant data persists

### Done when

Refreshing or navigating away does not unexpectedly destroy the customer's cart.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 6 — Checkout

### Objective

Build the order-request checkout experience.

### Customer fields

- [ ] First name
- [ ] Last name
- [ ] Email
- [ ] Phone
- [ ] Shipping address
- [ ] City
- [ ] State
- [ ] ZIP code
- [ ] Order notes

### Order information

- [ ] Items
- [ ] Variants
- [ ] Quantities
- [ ] Unit prices
- [ ] Subtotal

### UX

- [ ] Form validation
- [ ] Order summary
- [ ] Clear notice that payment is not collected online
- [ ] Prevent accidental duplicate submissions
- [ ] Mobile-friendly layout

### Required customer message

> No payment is collected online. After your order request is submitted, Starchild Clothing will contact you to confirm availability, payment, shipping/pickup, and fulfillment.

### Done when

A customer can complete the form and clearly understands what happens next.

**NEXT:** ______________________________________

---

# Long Break — 30–45 minutes

Completely disengage from the project.

---

## Pomodoro 7 — Order Submission

### Objective

Turn checkout into a real order request that Starchild receives.

### Tasks

- [ ] Implement order submission
- [ ] Validate payload server-side if using server functionality
- [ ] Generate an order reference/ID
- [ ] Include customer information
- [ ] Include cart contents
- [ ] Include variant details
- [ ] Include subtotal
- [ ] Include customer notes
- [ ] Send order to Starchild
- [ ] Show success state
- [ ] Clear cart only after successful submission
- [ ] Handle submission errors cleanly

### Example order reference

`SC-20260912-A8X4`

### Done when

A real test order reaches Starchild with enough information to manually fulfill it.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 8 — Production Cleanup

### Objective

Remove launch-blocking rough edges without adding new product features.

### Tasks

- [ ] Fix TypeScript errors
- [ ] Fix lint errors
- [ ] Fix build warnings that matter
- [ ] Remove console errors
- [ ] Check broken links
- [ ] Improve loading states
- [ ] Improve error states
- [ ] Verify form validation
- [ ] Verify empty states
- [ ] Check semantic HTML
- [ ] Check buttons vs links
- [ ] Check accessibility basics
- [ ] Verify environment variable handling
- [ ] Add metadata
- [ ] Add favicon
- [ ] Add sitemap
- [ ] Add `robots.txt`
- [ ] Optimize oversized images

### Done when

The production build is clean enough to ship and no P0 blocker remains.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 9 — Deployment

### Objective

Get the Starchild MVP onto its real production URL.

### Deployment decision

Use the repository audit to choose between:

#### Option A — Cloudflare static deployment

Use if the application does not require:

- Server Actions
- API routes
- SSR
- Runtime order-processing logic

#### Option B — Cloudflare Workers

Use if the application needs server-side order submission or other runtime functionality.

### Tasks

- [ ] Confirm deployment target
- [ ] Configure production build
- [ ] Configure environment variables
- [ ] Connect repository
- [ ] Deploy production build
- [ ] Configure custom domain
- [ ] Configure `www`/apex redirect
- [ ] Verify HTTPS
- [ ] Verify production asset loading
- [ ] Check production console for errors

### Done when

The public production URL loads successfully over HTTPS.

**NEXT:** ______________________________________

---

# Long Break — Dinner / 30–45 minutes

Do not immediately start fixing things just because the site is online.

---

## Pomodoro 10 — Real-World Production QA

### Objective

Test the website as an actual customer.

Use a phone on cellular data if possible.

### Test flow

- [ ] Open production URL
- [ ] Test navigation
- [ ] Browse every product
- [ ] Open every product page
- [ ] Verify images
- [ ] Select product variants
- [ ] Add product to cart
- [ ] Add multiple products
- [ ] Add two variants of the same product
- [ ] Refresh page
- [ ] Confirm cart persists
- [ ] Update quantity
- [ ] Remove item
- [ ] Verify subtotal
- [ ] Open checkout
- [ ] Enter customer information
- [ ] Submit real test order
- [ ] Confirm order reaches Starchild
- [ ] Verify confirmation state
- [ ] Test browser back button
- [ ] Test bad form input
- [ ] Verify no accidental duplicate submission
- [ ] Repeat critical flow on desktop

### Done when

A real order request succeeds from the production site.

**NEXT:** ______________________________________

---

## Break — 10 minutes

---

## Pomodoro 11 — Launch Blockers Only

### Objective

Fix only problems discovered during production QA that prevent launch.

### Allowed work

- Broken checkout
- Incorrect totals
- Missing product data
- Broken navigation
- Failed order notifications
- Mobile usability blockers
- Production errors
- HTTPS/domain problems

### Not allowed

- New features
- Visual redesign
- Admin dashboard
- Payments
- Database migration
- CMS
- Authentication
- "While we're here..." improvements

### Done when

All P0 launch blockers are resolved.

**NEXT:** Launch.

---

# Launch Gate

Do not call the MVP launched until all of these are true:

- [ ] Production domain resolves
- [ ] HTTPS works
- [ ] Homepage communicates the brand
- [ ] Every current product is accessible
- [ ] Product variants work
- [ ] Add to cart works
- [ ] Cart persists
- [ ] Quantity/remove work
- [ ] Cart totals are correct
- [ ] Checkout works
- [ ] A real test order has been submitted
- [ ] Starchild received the order
- [ ] Confirmation state works
- [ ] Mobile purchase flow passes
- [ ] No known P0 blockers remain

When complete:

```bash
git tag mvp-v1.0.0
```

---

# Codex Workflow

For each implementation block:

1. Give Codex one bounded objective.
2. Ask it to inspect existing patterns before changing architecture.
3. Tell it not to overengineer.
4. Have it run relevant build/type/lint checks.
5. Review the diff.
6. Commit the milestone.
7. Record nonessential ideas under Post-MVP.

Suggested commit structure:

```text
feat: production product catalog
feat: implement persistent shopping cart
feat: add order request checkout
feat: submit customer order requests
chore: production readiness cleanup
chore: configure production deployment
fix: resolve launch blockers
```

---

# Post-MVP Parking Lot

Put ideas here instead of interrupting today's launch.

- [ ] ______________________________________
- [ ] ______________________________________
- [ ] ______________________________________
- [ ] ______________________________________
- [ ] ______________________________________

---

# Final Objective

Today is successful when Starchild has a **real public storefront that accepts real customer order requests**.

It does not need to be the final ecommerce architecture.

It needs to work.
