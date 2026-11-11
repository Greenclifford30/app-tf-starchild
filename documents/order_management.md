
# Starchild Clothing — Order Management Implementation

## Objective

Extend the existing Starchild Clothing e-commerce MVP to support a reliable order management lifecycle, preparing the application for future online payment processing.

The application currently supports customer order requests. Introduce confirmed orders, administrative order management, and the foundations for inventory and payment processing.

**Prioritize simplicity, low operational costs, and compatibility with the existing architecture.**

## Existing Infrastructure

- **Frontend:** Next.js / React
- **Database:** Amazon DynamoDB
- **Authentication:** Amazon Cognito
- **Authorization:** Existing Cognito `Admin` group
- **Existing DynamoDB tables:**
  - `order_requests` — Must be preserved.
  - `products` — Already implemented and should be reused.
- **Current functionality:** Customer order-request submissions
- **Payment processing:** Not yet implemented

Before making changes, inspect the repository to understand existing infrastructure, API patterns, DynamoDB schemas, authentication, and deployment configuration.

Reuse existing conventions and infrastructure wherever practical.

---

## 1. Order Data Model

Introduce a dedicated DynamoDB `orders` table for confirmed purchases.

Each order should support:

- Unique order ID and human-readable order number
- Reference to the originating order request
- Customer contact information
- Order creation and modification timestamps
- Purchased items with product snapshots
- Subtotal, discounts, shipping, taxes, and total
- Currency
- Independent order, payment, and fulfillment statuses
- Shipping or pickup details
- Payment method and references
- Optimistic concurrency version

### Order Items

Store order items as nested attributes within the order document.

Each item should capture:

- Product ID
- SKU or variant ID, where applicable
- Product name
- Selected size and color
- Quantity
- Unit price at purchase
- Line total

**Historical order records must remain accurate even when product information or prices change.**

Store monetary amounts as integer cents and perform all authoritative calculations on the backend.

Consider DynamoDB's 400 KB item-size limit.

---

## 2. Order Lifecycle

Implement the following workflow:

1. Customer submits an order request using existing functionality.
2. An administrator reviews the request.
3. Administrator confirms availability and pricing.
4. Administrator converts the request into a confirmed order.
5. Order progresses through payment and fulfillment.
6. Order is marked completed or canceled as appropriate.

Maintain separate status fields.

### Order Status

- `CONFIRMED`
- `PROCESSING`
- `COMPLETED`
- `CANCELED`

### Payment Status

- `UNPAID`
- `PENDING`
- `PAID`
- `PARTIALLY_REFUNDED`
- `REFUNDED`
- `FAILED`

### Fulfillment Status

- `UNFULFILLED`
- `PROCESSING`
- `SHIPPED`
- `DELIVERED`
- `READY_FOR_PICKUP`
- `PICKED_UP`

Define and enforce valid status transitions on the backend.

Do not allow arbitrary status changes from API consumers.

Preserve the original `order_requests` records. Record the corresponding `orderId` or equivalent linkage when a request becomes an order.

Prevent the same request from creating multiple orders.

---

## 3. DynamoDB Access Patterns

Design DynamoDB keys and GSIs around these operations:

- Retrieve order by ID.
- List orders newest first.
- Filter orders by order status.
- Retrieve an order by originating request.
- Retrieve customer orders when needed.
- Retrieve orders requiring fulfillment.

### Guidelines

- Prefer efficient `Query` operations over `Scan`.
- Avoid unnecessary secondary indexes.
- Use conditional writes for concurrency protection.
- Use optimistic concurrency for administrative updates.
- Use DynamoDB transactions when multiple records must be updated atomically.
- Implement paginated list operations.
- Avoid introducing additional tables unless justified by access patterns.

---

## 4. Administrative API and Authorization

Leverage the existing Cognito `Admin` group.

Implement or extend backend endpoints supporting:

- List orders with pagination and filtering.
- Retrieve order details.
- Convert an order request into a confirmed order.
- Update order status.
- Update payment status.
- Update fulfillment status.
- Record shipment or pickup information.
- Cancel an order.

### Authorization Requirements

- Protect all administrative operations.
- Validate Cognito authentication tokens server-side.
- Enforce Cognito `Admin` group membership.
- Do not rely on frontend visibility or client-side checks.
- Follow existing API conventions and error-handling patterns.

---

## 5. Administrative User Interface

Extend the existing administration experience to provide:

- Order list with status indicators
- Individual order detail view
- Customer contact information
- Purchased items and financial breakdown
- Confirmation of pending order requests
- Order, payment, and fulfillment management
- Shipping tracking information, where applicable

Reuse existing components and design conventions.

Prioritize a straightforward workflow that allows the business owner to manage orders without developer assistance.

---

## 6. Inventory Readiness

Review the existing `products` table to determine how products, sizes, colors, and quantities are represented.

Recommend the minimum changes needed to support SKU- or variant-level inventory.

The inventory model should eventually support:

- Tracking available quantities
- Preventing overselling
- Reserving inventory when orders are confirmed
- Releasing reserved inventory when appropriate
- Handling canceled orders

### Implementation Guidelines

- Use conditional DynamoDB updates for stock changes.
- Use transactions when inventory and order updates must be atomic.
- Do not introduce a separate inventory table unless justified.
- Do not invent stock counts or treat untracked inventory as available.
- Document limitations if inventory tracking is deferred.

---

## 7. Payment Integration Readiness

**Do not implement a payment processor yet.**

Prepare the order model for future hosted checkout and payment-provider webhooks.

Consider:

- Payment provider identifiers
- External transaction references
- Payment timestamps
- Idempotent payment processing
- Full and partial refunds
- Payment reconciliation
- Payment-related order events

### Payment Security

- Never store sensitive payment card information.
- Do not trust client-reported payment success.
- Future payment confirmations must rely on verified provider events.
- Support manually recorded payments for the initial workflow.
- Restrict manual payment updates to authorized administrators.
- Maintain audit information for payment changes.

---

## 8. Order Audit History

Implement a lightweight, durable order-event history.

Track significant events including:

- Order confirmed
- Order status changed
- Payment recorded
- Order shipped
- Order delivered
- Order canceled
- Refund recorded, when supported

Each event should capture:

- Event ID
- Order ID
- Event type
- Timestamp
- Responsible actor, where applicable
- Relevant status changes or metadata

Evaluate whether a separate `order_events` table or another DynamoDB modeling approach best fits the project.

Avoid storing an unbounded event-history array within the order document.

---

## 9. Reliability and Security

Account for:

- Duplicate order requests and retries
- Atomic request-to-order conversion
- Server-side price verification
- Input validation
- API authorization
- Concurrent administrative modifications
- Appropriate error responses
- Pagination and bounded queries
- Customer data protection
- Logging without exposing sensitive information
- Idempotent order creation and status changes

Ensure failed or repeated operations cannot create inconsistent orders or duplicate inventory deductions.

---

## 10. Testing and Documentation

Add tests covering:

- Successful request-to-order conversion
- Duplicate conversion prevention
- Unauthorized administrative requests
- Invalid order-state transitions
- Order total calculations
- Product snapshot preservation
- Concurrent administrative updates
- Inventory validation, where implemented

Update relevant:

- Infrastructure definitions
- API contracts
- Backend documentation
- DynamoDB schema documentation
- Environment configuration
- Deployment documentation

Document DynamoDB partition keys, sort keys, GSIs, and supported access patterns.

Include migration or backfill considerations if existing records need modification.

---

## 11. Implementation Strategy

Work in two phases.

### Phase 1 — Functional Order Management

Implement:

1. Inspect existing application and infrastructure.
2. Introduce confirmed order persistence.
3. Link order requests to confirmed orders.
4. Implement protected administrative APIs.
5. Add basic administrative order management UI.
6. Enforce order lifecycle transitions.
7. Introduce durable audit events.
8. Add appropriate automated tests.

### Phase 2 — Commerce Readiness

Prepare or propose incremental improvements for:

1. Variant-level inventory management.
2. Inventory reservation and release.
3. Future payment integration.
4. Refund handling.
5. Shipping and tax integrations.
6. Customer notifications.

**Do not implement all Phase 2 functionality prematurely.**

---

## 12. Deliverables

1. Brief assessment of existing architecture and identified gaps.
2. Recommended DynamoDB order schema and access patterns.
3. Implementation of Phase 1 using existing project conventions.
4. Infrastructure changes for new resources, indexes, or IAM permissions.
5. Administrative order management UI.
6. Tests covering critical order workflows.
7. Documentation of implementation details and future enhancements.

---

## 13. Important Constraints

- **Preserve the existing `order_requests` table.**
- **Reuse the existing `products` table.**
- **Reuse the existing Cognito `Admin` group.**
- Do not migrate to PostgreSQL or another database.
- Do not introduce microservices or unnecessary AWS infrastructure.
- Do not implement online payment processing yet.
- Avoid breaking existing customer order-request functionality.
- Keep infrastructure costs minimal.
- Follow established repository patterns rather than introducing a new architectural style.
- Prefer incremental changes over significant refactoring.

---

## 14. Execution Instructions for Codex

### Step 1 — Repository Analysis

Inspect the repository and identify:

- Existing DynamoDB tables and schemas
- Current order-request submission workflow
- Product data structures
- Cognito authentication and authorization implementation
- Backend API patterns
- Existing administrative components
- Infrastructure-as-code configuration
- Existing automated tests

### Step 2 — Implementation Plan

Produce a concise implementation plan covering:

- Proposed DynamoDB order schema
- Required backend endpoints
- Required administrative UI changes
- Infrastructure changes
- Authorization requirements
- Testing strategy

Identify opportunities to reuse existing code.

### Step 3 — Phase 1 Implementation

Execute Phase 1 according to the plan.

Implement the necessary backend, frontend, and infrastructure changes.

Ensure existing functionality remains intact.

### Step 4 — Validation

Run relevant tests, linting, and build checks.

Fix identified implementation issues where possible.

Document any remaining limitations.

### Step 5 — Final Summary

Provide a summary containing:

- Changes implemented
- Files modified or created
- DynamoDB resources introduced
- API endpoints added
- Administrative UI functionality
- Tests executed and results
- Outstanding issues
- Recommended Phase 2 enhancements

**Do not stop at planning or schema design. Implement Phase 1, validate the result, and document the outcome.**

Make reasonable decisions based on the existing codebase and document assumptions or architectural tradeoffs.

---

## Phase 1 implementation decisions

The implemented administrator group is `starchild-admin`. Requests retain their existing table and receive a review-status index; confirmed orders, separate event items, number reservations, and operation-id records live in one new on-demand table. The schema, API contracts, deployment/backfill steps, and supported access patterns are documented in `infra/README.md`.

Administrators confirm current catalog prices and manually verified availability, with order-level discount, shipping, and tax adjustments. They may decline a request with a reason. Shipping and pickup are supported; payment is required before handoff and can be recorded together with pickup. Paid cancellations before handoff are flagged for an external refund. Full payments are recorded manually; partial payments and refund processing are deferred. Inventory is not tracked or reserved.

Acceptance is an authorized administrator reviewing an existing request, confirming it once, recording payment, fulfilling by shipping or pickup, and inspecting durable history. Customer order requests and their existing public endpoint remain available. Phase 2 covers variant stock and reservations, hosted payment and verified webhooks, refunds, shipping and tax integrations, and customer notifications.
