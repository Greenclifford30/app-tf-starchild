"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

type Customer = { first_name: string; last_name: string; email: string; phone: string; address: string; address_line_2?: string; city: string; state: string; postal_code: string; country: string; notes?: string };
type Item = { product_slug: string; name: string; color: string; size: string; quantity: number; unit_price_cents: number; line_total_cents: number };
type RequestRecord = { submission_id: string; order_reference: string; created_at: string; customer: Customer; items: Item[]; subtotal_cents: number; shipping_cents: number; total_cents: number; review_status?: string; decline_reason?: string; order_id?: string; payment_provider?: string; payment_status?: string; capture_before?: number; tax_cents?: number };
type Order = { order_id: string; order_number: string; request_reference: string; created_at: string; customer: Customer; items: Item[]; subtotal_cents: number; shipping_cents: number; discount_cents: number; tax_cents: number; total_cents: number; adjustment_reason?: string; order_status: string; payment_status: string; fulfillment_status: string; fulfillment_method: string; pickup_instructions?: string; refund_follow_up: boolean; cancel_reason?: string; version: number; payment_provider?: string; capture_before?: number; payment?: { method: string; reference?: string; amount_cents: number; recorded_at: string }; shipment?: { carrier: string; tracking?: string } };
type Event = { event_id: string; event_type: string; created_at: string; actor: string; metadata: Record<string, unknown> };
type Preview = { items: Item[]; subtotal_cents: number; quoteToken: string };
type Page<T> = { nextCursor: string | null } & T;
type View = "requests" | "orders";

const root = "/api/admin/order-management";
const money = (cents: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);
const label = (value: string) => value.replaceAll("_", " ").toLowerCase();
const date = (value: string) => new Date(value).toLocaleString();
const cents = (value: string) => Math.round(Number(value) * 100);

async function api<T>(path: string, payload?: object): Promise<T> {
  const response = await fetch(root + path, payload ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload) } : { cache: "no-store" });
  const result = await response.json().catch(() => ({ message: "The order service returned an invalid response." }));
  if (response.status === 401 || response.status === 403) throw new Error("Your administrator session is unavailable. Sign in again from the catalog page.");
  if (!response.ok) throw new Error(result.message || "The order service is unavailable.");
  return result as T;
}

export default function OrderManager() {
  const [view, setView] = useState<View>("requests");
  const [filter, setFilter] = useState("PENDING");
  const [requests, setRequests] = useState<RequestRecord[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [request, setRequest] = useState<RequestRecord | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState("");
  const [order, setOrder] = useState<Order | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventCursor, setEventCursor] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [method, setMethod] = useState("SHIPPING");
  const [pickup, setPickup] = useState("");
  const [discount, setDiscount] = useState("0.00");
  const [shipping, setShipping] = useState("0.00");
  const [tax, setTax] = useState("0.00");
  const [adjustment, setAdjustment] = useState("");
  const [available, setAvailable] = useState(false);
  const [reason, setReason] = useState("");
  const [paymentMethod, setPaymentMethod] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [carrier, setCarrier] = useState("");
  const [tracking, setTracking] = useState("");
  const [pendingOperation, setPendingOperation] = useState<{ fingerprint: string; id: string } | null>(null);

  const loadList = useCallback(async (next?: string) => {
    setLoading(true); setError("");
    try {
      const search = new URLSearchParams();
      if (next) search.set("cursor", next);
      if (view === "requests") {
        search.set("status", filter);
        const result = await api<Page<{ requests: RequestRecord[] }>>(`/order-requests?${search}`);
        setRequests((old) => next ? [...old, ...result.requests] : result.requests); setCursor(result.nextCursor);
      } else {
        if (filter === "OPEN") search.set("fulfillment", "open");
        else if (filter !== "ALL") search.set("status", filter);
        const result = await api<Page<{ orders: Order[] }>>(`/orders?${search}`);
        setOrders((old) => next ? [...old, ...result.orders] : result.orders); setCursor(result.nextCursor);
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load orders."); }
    finally { setLoading(false); }
  }, [view, filter]);
  useEffect(() => { void loadList(); }, [loadList]);

  async function openRequest(id: string) {
    setBusy(true); setError(""); setNotice(""); setOrder(null); setReason("");
    try {
      const result = await api<{ request: RequestRecord; preview: Preview | null; previewError?: string }>(`/order-requests/${id}`);
      setRequest(result.request); setPreview(result.preview); setPreviewError(result.previewError || "");
      setMethod("SHIPPING"); setShipping((result.request.shipping_cents / 100).toFixed(2)); setTax("0.00"); setDiscount("0.00"); setAdjustment(""); setPickup(""); setAvailable(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the request."); }
    finally { setBusy(false); }
  }
  async function openOrder(id: string) {
    setBusy(true); setError(""); setNotice(""); setRequest(null); setReason(""); setPendingOperation(null);
    try {
      const [details, history] = await Promise.all([api<{ order: Order }>(`/orders/${id}`), api<Page<{ events: Event[] }>>(`/orders/${id}/events`)]);
      setOrder(details.order); setEvents(history.events); setEventCursor(history.nextCursor);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not load the order."); }
    finally { setBusy(false); }
  }
  function switchView(next: View) { setView(next); setFilter(next === "requests" ? "PENDING" : "ALL"); setRequest(null); setOrder(null); setCursor(null); setNotice(""); }
  async function confirmRequest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!request || !preview) return;
    setBusy(true); setError("");
    try {
      const result = await api<{ order: Order }>(`/order-requests/${request.submission_id}/confirm`, { quoteToken: preview.quoteToken, availabilityConfirmed: available, fulfillmentMethod: method, pickupInstructions: pickup, discountCents: cents(discount), shippingCents: cents(shipping), taxCents: cents(tax), adjustmentReason: adjustment });
      setView("orders"); setFilter("ALL"); setRequest(null); await openOrder(result.order.order_id); setNotice(request.payment_provider === "stripe" ? "Order confirmed. Stripe is processing the capture; reload to check its status." : "Order confirmed. The request is now linked to this order.");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not confirm this request."); }
    finally { setBusy(false); }
  }
  async function declineRequest() {
    if (!request) return;
    setBusy(true); setError("");
    try { await api(`/order-requests/${request.submission_id}/decline`, { reason }); setRequest(null); setNotice("Request declined."); await loadList(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not decline this request."); }
    finally { setBusy(false); }
  }
  async function perform(action: string, extra: Record<string, string> = {}) {
    if (!order) return;
    setBusy(true); setError(""); setNotice("");
    const content = { action, version: order.version, ...extra };
    const fingerprint = JSON.stringify(content);
    const operationId = pendingOperation?.fingerprint === fingerprint ? pendingOperation.id : crypto.randomUUID();
    setPendingOperation({ fingerprint, id: operationId });
    try {
      const result = await api<{ order: Order }>(`/orders/${order.order_id}/actions`, { ...content, operationId });
      setOrder(result.order); setPendingOperation(null); setNotice("Order updated.");
      const history = await api<Page<{ events: Event[] }>>(`/orders/${order.order_id}/events`); setEvents(history.events); setEventCursor(history.nextCursor);
      await loadList();
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update this order."); }
    finally { setBusy(false); }
  }
  async function moreEvents() {
    if (!order || !eventCursor) return;
    setBusy(true);
    try { const result = await api<Page<{ events: Event[] }>>(`/orders/${order.order_id}/events?cursor=${encodeURIComponent(eventCursor)}`); setEvents((old) => [...old, ...result.events]); setEventCursor(result.nextCursor); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not load history."); }
    finally { setBusy(false); }
  }
  const selected = request || order;
  return <main className="orders-page">
    <header className="orders-header"><div><h1>Requests &amp; orders</h1><p>Review requests and manage fulfillment.</p></div><nav aria-label="Administration"><a href="/admin">Catalog</a><a href="/shop" target="_blank" rel="noreferrer">View store</a><button className="orders-link" type="button" onClick={() => { void fetch("/api/admin/session", { method: "DELETE" }).then(() => { window.location.href = "/admin"; }); }}>Sign out</button></nav></header>
    <div className="orders-layout"><aside className="orders-sidebar">
      <div className="orders-tabs"><button type="button" aria-pressed={view === "requests"} onClick={() => switchView("requests")}>Requests</button><button type="button" aria-pressed={view === "orders"} onClick={() => switchView("orders")}>Orders</button></div>
      <label className="orders-filter">Show<select value={filter} onChange={(e) => { setFilter(e.target.value); setRequest(null); setOrder(null); }}>
        {view === "requests" ? <><option value="PENDING">Pending requests</option><option value="CONVERTED">Confirmed requests</option><option value="DECLINED">Declined requests</option></> : <><option value="ALL">All orders</option><option value="OPEN">Awaiting fulfillment</option><option value="CONFIRMED">Confirmed</option><option value="PROCESSING">Processing</option><option value="COMPLETED">Completed</option><option value="CANCELED">Canceled</option></>}
      </select></label>
      {loading && !cursor ? <p className="orders-muted" role="status">Loading…</p> : null}
      {!loading && !(view === "requests" ? requests.length : orders.length) ? <p className="orders-muted">No {view} in this view.</p> : null}
      <div className="orders-list">{view === "requests" ? requests.map((entry) => <button type="button" className={request?.submission_id === entry.submission_id ? "selected" : ""} key={entry.submission_id} onClick={() => void openRequest(entry.submission_id)}><strong>{entry.order_reference}</strong><span>{date(entry.created_at)} · {money(entry.total_cents)}</span></button>) : orders.map((entry) => <button type="button" className={order?.order_id === entry.order_id ? "selected" : ""} key={entry.order_id} onClick={() => void openOrder(entry.order_id)}><strong>{entry.order_number}</strong><span>{label(entry.order_status)} · {money(entry.total_cents)}</span>{entry.refund_follow_up ? <span>Refund follow-up needed</span> : null}</button>)}</div>
      {cursor ? <button className="orders-link" type="button" disabled={loading} onClick={() => void loadList(cursor)}>Load more</button> : null}
    </aside><section className="orders-content" aria-live="polite">
      {error ? <p className="orders-error" role="alert">{error} {order ? <button type="button" className="orders-link" onClick={() => void openOrder(order.order_id)}>Reload order</button> : request ? <button type="button" className="orders-link" onClick={() => void openRequest(request.submission_id)}>Reload request</button> : <a href="/admin">Go to sign in</a>}</p> : null}
      {notice ? <p className="orders-notice" role="status">{notice}</p> : null}
      {!selected ? <div className="orders-empty"><h2>Select a {view === "requests" ? "request" : "order"}</h2><p>Choose an item from the list to view its details and available actions.</p></div> : null}
      {request ? <><div className="orders-title"><div><p className="orders-overline">Order request · {label(request.review_status || "PENDING")}</p><h2>{request.order_reference}</h2><p>Received {date(request.created_at)}</p></div>{request.order_id ? <button type="button" className="button button-secondary" onClick={() => { setView("orders"); setFilter("ALL"); void openOrder(request.order_id!); }}>View order</button> : null}</div>
        <CustomerDetails customer={request.customer} />
        <section className="orders-section"><h3>Requested items</h3><Items items={request.items} /><Totals values={request.payment_provider === "stripe" ? [["Subtotal", request.subtotal_cents], ["Shipping", request.shipping_cents], ["Tax", request.tax_cents || 0], ["Authorized total", request.total_cents]] : [["Estimated subtotal", request.subtotal_cents], ["Estimated shipping", request.shipping_cents], ["Estimated total", request.total_cents]]} />{request.payment_provider === "stripe" ? <p>Payment hold: <strong>{label(request.payment_status || "PENDING")}</strong>{request.capture_before ? ` · Expires ${date(new Date(request.capture_before * 1000).toISOString())}` : ""}</p> : null}</section>
        {request.decline_reason ? <p>Declined: {request.decline_reason}</p> : null}
        {(request.review_status || "PENDING") === "PENDING" ? <section className="orders-section"><h3>Confirm order</h3><p className="orders-muted">Stock is not tracked in the app. Verify each item is available before confirming.</p>
          {previewError ? <p className="orders-error" role="alert">{previewError}</p> : null}
          {preview && request.payment_provider === "stripe" ? <form className="orders-form" onSubmit={confirmRequest}><p>The authorized total is fixed. Confirm availability to capture {money(request.total_cents)}.</p><label className="orders-check"><input type="checkbox" checked={available} onChange={(e) => setAvailable(e.target.checked)} required /> I verified availability.</label><button className="button button-primary" disabled={busy || !available || request.payment_status !== "AUTHORIZED"}>Confirm and capture payment</button></form> : null}
          {preview && request.payment_provider !== "stripe" ? <form className="orders-form" onSubmit={confirmRequest}><h4>Current catalog prices</h4><Items items={preview.items} /><p>Current subtotal <strong>{money(preview.subtotal_cents)}</strong></p>
            <div className="orders-fields"><label>Fulfillment<select value={method} onChange={(e) => { setMethod(e.target.value); setShipping(e.target.value === "PICKUP" ? "0.00" : (request.shipping_cents / 100).toFixed(2)); }}><option value="SHIPPING">Shipping</option><option value="PICKUP">Pickup</option></select></label><label>Discount ($)<input type="number" min="0" step="0.01" value={discount} onChange={(e) => setDiscount(e.target.value)} required /></label><label>Shipping ($)<input type="number" min="0" step="0.01" value={shipping} onChange={(e) => setShipping(e.target.value)} disabled={method === "PICKUP"} required /></label><label>Tax ($)<input type="number" min="0" step="0.01" value={tax} onChange={(e) => setTax(e.target.value)} required /></label></div>
            {method === "PICKUP" ? <label>Pickup instructions<textarea value={pickup} onChange={(e) => setPickup(e.target.value)} maxLength={500} required /></label> : null}
            <label>Adjustment explanation <span className="orders-muted">Required when amounts differ from defaults</span><textarea value={adjustment} onChange={(e) => setAdjustment(e.target.value)} maxLength={500} /></label>
            <p>Final total <strong>{money(preview.subtotal_cents - cents(discount || "0") + cents(shipping || "0") + cents(tax || "0"))}</strong></p>
            <label className="orders-check"><input type="checkbox" checked={available} onChange={(e) => setAvailable(e.target.checked)} required /> I verified availability and reviewed current prices.</label><button className="button button-primary" disabled={busy || !available}>Confirm order</button>
          </form> : null}
          <div className="orders-subsection"><h4>Decline request</h4><label>Reason<textarea value={reason} onChange={(e) => setReason(e.target.value)} maxLength={500} /></label><button type="button" className="button button-secondary" disabled={busy || !reason.trim()} onClick={() => void declineRequest()}>Decline request</button></div>
        </section> : null}</> : null}
      {order ? <><div className="orders-title"><div><p className="orders-overline">Confirmed order · {order.request_reference}</p><h2>{order.order_number}</h2><p>Created {date(order.created_at)}</p></div></div>
        {order.refund_follow_up ? <p className="orders-warning" role="status"><strong>Refund follow-up needed.</strong> {order.payment_provider === "stripe" ? (order.payment_status === "REFUND_FAILED" ? "The refund failed. Check Stripe and arrange another way to refund the customer." : "This order was paid and canceled. Use the refund action below.") : "This order was paid and canceled. Handle the refund outside the application."}</p> : null}
        <div className="orders-status"><span>Order <strong>{label(order.order_status)}</strong></span><span>Payment <strong>{label(order.payment_status)}</strong></span><span>Fulfillment <strong>{label(order.fulfillment_status)}</strong></span></div>
        <CustomerDetails customer={order.customer} /><section className="orders-section"><h3>Items &amp; totals</h3><Items items={order.items} /><Totals values={[["Subtotal", order.subtotal_cents], ["Discount", -order.discount_cents], ["Shipping", order.shipping_cents], ["Tax", order.tax_cents], ["Total", order.total_cents]]} />{order.adjustment_reason ? <p>Adjustment: {order.adjustment_reason}</p> : null}</section>
        <section className="orders-section"><h3>Payment &amp; fulfillment</h3>{order.payment_provider === "stripe" && order.payment_status === "FAILED" ? <p className="orders-error" role="status">The payment hold expired or was canceled. Cancel this order and contact the customer about a new checkout.</p> : null}{order.payment_provider === "stripe" && order.payment_status === "PENDING" ? <p>Capture is pending. Reload to check Stripe’s confirmation, or retry capture. {order.capture_before ? `Hold expires ${date(new Date(order.capture_before * 1000).toISOString())}.` : ""} <button type="button" className="orders-link" disabled={busy} onClick={() => void perform("CAPTURE_STRIPE")}>Retry capture</button></p> : null}{order.payment_provider === "stripe" && order.order_status === "CANCELED" && ["PAID", "REFUND_PENDING"].includes(order.payment_status) ? <p><button type="button" className="button button-secondary" disabled={busy} onClick={() => void perform("REFUND_STRIPE")}>{order.payment_status === "REFUND_PENDING" ? "Retry refund" : "Refund full payment"}</button></p> : null}<p>Method: {label(order.fulfillment_method)}{order.pickup_instructions ? ` · ${order.pickup_instructions}` : ""}</p>{order.payment ? <p>Payment: {money(order.payment.amount_cents)} via {order.payment.method}{order.payment.reference ? ` · ${order.payment.reference}` : ""} · {date(order.payment.recorded_at)}</p> : <p>Payment has not been recorded.</p>}{order.shipment ? <p>Shipment: {order.shipment.carrier}{order.shipment.tracking ? ` · ${order.shipment.tracking}` : ""}</p> : null}{order.cancel_reason ? <p>Cancellation: {order.cancel_reason}</p> : null}
          {!['COMPLETED', 'CANCELED'].includes(order.order_status) ? <div className="orders-form">
            {order.payment_status === "UNPAID" && order.payment_provider !== "stripe" ? <div className="orders-subsection"><h4>Record payment</h4><div className="orders-fields"><label>Payment method<input value={paymentMethod} maxLength={80} onChange={(e) => setPaymentMethod(e.target.value)} placeholder="Cash, bank transfer…" /></label><label>Reference (optional)<input value={paymentReference} maxLength={160} onChange={(e) => setPaymentReference(e.target.value)} /></label></div><button type="button" className="button button-secondary" disabled={busy || !paymentMethod.trim()} onClick={() => void perform("RECORD_PAYMENT", { paymentMethod, paymentReference })}>Record {money(order.total_cents)} payment</button>{order.fulfillment_status === "READY_FOR_PICKUP" ? <button type="button" className="button button-secondary" disabled={busy || !paymentMethod.trim()} onClick={() => void perform("PICKED_UP_AND_PAY", { paymentMethod, paymentReference })}>Record payment &amp; complete pickup</button> : null}</div> : null}
            {order.order_status === "CONFIRMED" ? <button type="button" className="button button-primary" disabled={busy} onClick={() => void perform("START_PROCESSING")}>Start preparation</button> : null}
            {order.fulfillment_status === "PROCESSING" && order.fulfillment_method === "PICKUP" ? <button type="button" className="button button-primary" disabled={busy} onClick={() => void perform("READY_FOR_PICKUP")}>Mark ready for pickup</button> : null}
            {order.fulfillment_status === "PROCESSING" && order.fulfillment_method === "SHIPPING" ? <div className="orders-subsection"><h4>Ship order</h4><p className="orders-muted">Payment must be recorded before shipment.</p><div className="orders-fields"><label>Carrier<input value={carrier} onChange={(e) => setCarrier(e.target.value)} maxLength={100} /></label><label>Tracking number (optional)<input value={tracking} onChange={(e) => setTracking(e.target.value)} maxLength={160} /></label></div><button type="button" className="button button-primary" disabled={busy || order.payment_status !== "PAID" || !carrier.trim()} onClick={() => void perform("SHIP", { carrier, tracking })}>Mark shipped</button></div> : null}
            {order.fulfillment_status === "SHIPPED" ? <button type="button" className="button button-primary" disabled={busy} onClick={() => void perform("DELIVER")}>Mark delivered</button> : null}
            {order.fulfillment_status === "READY_FOR_PICKUP" && order.payment_status === "PAID" ? <button type="button" className="button button-primary" disabled={busy} onClick={() => void perform("PICK_UP")}>Complete pickup</button> : null}
            {order.fulfillment_status !== "SHIPPED" ? <div className="orders-subsection"><h4>Cancel order</h4>{order.payment_status === "PAID" ? <p className="orders-muted">{order.payment_provider === "stripe" ? "After cancellation, use the refund action to return payment." : "A paid cancellation needs an external refund follow-up."}</p> : null}<label>Reason<textarea value={reason} maxLength={500} onChange={(e) => setReason(e.target.value)} /></label><button type="button" className="button button-secondary" disabled={busy || !reason.trim()} onClick={() => void perform("CANCEL", { reason })}>Cancel order</button></div> : null}
          </div> : null}
        </section><section className="orders-section"><h3>History</h3><ol className="orders-history">{events.map((entry) => <li key={entry.event_id}><strong>{label(entry.event_type)}</strong><span>{date(entry.created_at)} · {entry.actor}</span><details><summary>Details</summary><pre>{JSON.stringify(entry.metadata, null, 2)}</pre></details></li>)}</ol>{eventCursor ? <button className="orders-link" type="button" disabled={busy} onClick={() => void moreEvents()}>Load more history</button> : null}</section></> : null}
    </section></div>
  </main>;
}

function CustomerDetails({ customer }: { customer: Customer }) { return <section className="orders-section"><h3>Customer</h3><p><strong>{customer.first_name} {customer.last_name}</strong><br /><a href={`mailto:${customer.email}`}>{customer.email}</a><br />{customer.phone}</p><p>{customer.address}{customer.address_line_2 ? `, ${customer.address_line_2}` : ""}<br />{customer.city}, {customer.state} {customer.postal_code} {customer.country}</p>{customer.notes ? <p>Customer note: {customer.notes}</p> : null}</section>; }
function Items({ items }: { items: Item[] }) { return <ul className="orders-items">{items.map((item, i) => <li key={`${item.product_slug}-${item.color}-${item.size}-${i}`}><div><strong>{item.name}</strong><span>{item.color} / {item.size} · {item.quantity} × {money(item.unit_price_cents)}</span></div><strong>{money(item.line_total_cents)}</strong></li>)}</ul>; }
function Totals({ values }: { values: [string, number][] }) { return <dl className="orders-totals">{values.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{money(value)}</dd></div>)}</dl>; }
