"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckoutForm as StripeForm, CheckoutFormProvider, useCheckoutForm } from "@stripe/react-stripe-js/checkout";
import { loadStripe } from "@stripe/stripe-js";
import { useCart } from "../cart";

const publishableKey = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
const stripePromise = publishableKey ? loadStripe(publishableKey) : null;
const attemptStorageKey = "starchild-checkout-attempt";
const formatPrice = (value: number) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

type Attempt = { id: string; bag: string };
type SessionResponse = { clientSecret?: string; message?: string };
type StatusResponse = { status: string; orderReference?: string; message?: string };

function PaymentForm() {
  const checkout = useCheckoutForm();
  const [error, setError] = useState("");
  if (checkout.type === "error") return <p className="checkout-error" role="alert">{checkout.error.message}</p>;
  return <><StripeForm onConfirm={async (event) => {
    if (checkout.type !== "success") return;
    setError("");
    try { await checkout.checkout.confirm({ formConfirmEvent: event }); }
    catch { setError("We could not finish checkout. Please try again."); }
  }} />{error ? <p className="checkout-error" role="alert">{error}</p> : null}</>;
}

export default function CheckoutForm() {
  const { items, hydrated, subtotal, updateQuantity, removeItem, clearCart } = useCart();
  const [clientSecret, setClientSecret] = useState("");
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [started, setStarted] = useState(false);
  const [checking, setChecking] = useState(false);
  const [orderReference, setOrderReference] = useState("");
  const [captured, setCaptured] = useState(false);
  const [returnUnknown, setReturnUnknown] = useState(false);
  const [error, setError] = useState("");
  const apiBase = process.env.NEXT_PUBLIC_PAYMENTS_API_URL;
  const bag = useMemo(() => JSON.stringify(items.map(({ productSlug, color, size, quantity }) => ({ productSlug, color, size, quantity }))), [items]);
  const shipping = subtotal >= 100 ? 0 : 8;
  const stripeOptions = useMemo(() => ({ clientSecret, appearance: { theme: "flat" as const, variables: { colorPrimary: "#10172b", colorText: "#10172b", fontFamily: "Arial, sans-serif", borderRadius: "4px" } } }), [clientSecret]);

  const checkStatus = useCallback(async (current: Attempt) => {
    if (!apiBase) return;
    try {
      const sessionId = new URLSearchParams(window.location.search).get("session_id") || "";
      const response = await fetch(`${apiBase}/checkout/sessions/${encodeURIComponent(current.id)}?session_id=${encodeURIComponent(sessionId)}`, { cache: "no-store" });
      const result = await response.json() as StatusResponse;
      if (!response.ok) throw new Error(result.message || "We could not check your order.");
      if (["AUTHORIZED", "PAID"].includes(result.status) && result.orderReference) {
        if (current.bag === bag) clearCart();
        sessionStorage.removeItem(attemptStorageKey);
        setCaptured(result.status === "PAID"); setOrderReference(result.orderReference); setChecking(false);
      } else if (["CANCELED", "UPDATED"].includes(result.status)) {
        sessionStorage.removeItem(attemptStorageKey); setChecking(false); setReturnUnknown(true); setError("Your order status has changed. Please check your email or contact us for help.");
      } else if (result.status === "EXPIRED") {
        sessionStorage.removeItem(attemptStorageKey);
        setChecking(false); setError("This checkout expired. Please start again.");
      }
    } catch { setError("We are still checking your order. Please refresh this page or contact us if this continues."); }
  }, [apiBase, bag, clearCart]);

  useEffect(() => {
    if (!hydrated || !new URLSearchParams(window.location.search).has("session_id")) return;
    try {
      const stored = JSON.parse(sessionStorage.getItem(attemptStorageKey) || "null") as Attempt | null;
      if (stored?.id && stored.bag) { setAttempt(stored); setChecking(true); }
      else { setReturnUnknown(true); setError("Please check your email for your order status or contact us before placing another order."); }
    } catch { setReturnUnknown(true); setError("Please check your email for your order status or contact us before placing another order."); }
  }, [hydrated]);

  useEffect(() => {
    if (!checking || !attempt) return;
    void checkStatus(attempt);
    const timer = window.setInterval(() => void checkStatus(attempt), 4000);
    return () => window.clearInterval(timer);
  }, [attempt, checking, checkStatus]);

  async function startCheckout() {
    if (!apiBase || !stripePromise) { setError("Checkout is temporarily unavailable. Please try again shortly."); return; }
    setStarted(true); setError("");
    try {
      let current: Attempt | null = null;
      try { current = JSON.parse(sessionStorage.getItem(attemptStorageKey) || "null") as Attempt | null; } catch { /* Start a new attempt. */ }
      if (!current?.id || current.bag !== bag) current = { id: crypto.randomUUID(), bag };
      sessionStorage.setItem(attemptStorageKey, JSON.stringify(current));
      setAttempt(current);
      const response = await fetch(`${apiBase}/checkout/sessions`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ attemptId: current.id, items: JSON.parse(bag) }) });
      const result = await response.json() as SessionResponse;
      if (!response.ok || !result.clientSecret) throw new Error(result.message || "We could not start checkout. Please try again.");
      setClientSecret(result.clientSecret);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "We could not start checkout. Please try again."); setStarted(false); }
  }

  if (orderReference) return <section className="order-confirmation" aria-labelledby="confirmation-title"><h1 id="confirmation-title">{captured ? "Your order is confirmed." : "Your order is under review."}</h1><p className="confirmation-lede">We received order <strong>{orderReference}</strong>. {captured ? "Your payment has been captured." : "A temporary hold is on your payment."}</p><p>{captured ? "You’ll receive an email with the details." : "We’ll check availability and capture payment when your order is confirmed. You’ll receive an email with the details."}</p><Link className="button button-primary" href="/shop">Keep shopping</Link></section>;
  if (returnUnknown) return <section className="order-confirmation" aria-live="polite"><h1>Checking your order.</h1><p role="alert">{error}</p><Link className="button button-secondary" href="/">Return home</Link></section>;
  if (checking) return <section className="order-confirmation" aria-live="polite"><h1>Checking your order.</h1><p>We’re confirming your payment authorization. Please keep this page open.</p>{error ? <p className="checkout-error" role="alert">{error}</p> : null}</section>;
  if (hydrated && items.length === 0) return <section className="checkout-empty"><h1>Your orbit is empty.</h1><p>Choose a piece and select its size before checking out.</p><Link className="button button-primary" href="/shop">Explore the collection</Link></section>;

  return <div className="checkout-layout">
    <section className="checkout-form" aria-labelledby="checkout-title">
      <div className="checkout-intro"><h1 id="checkout-title">One step closer.</h1><p>Authorize your payment now. We’ll confirm availability before charging you.</p></div>
      <div className="checkout-section"><h2>Contact, delivery &amp; payment</h2><p>Choose Apple Pay, Google Pay, or a card. Tax and the final total appear before you authorize payment.</p>
        {!clientSecret ? <button className="button button-primary checkout-submit" type="button" onClick={() => void startCheckout()} disabled={!hydrated || started || !items.length}>{started ? "Preparing checkout…" : "Continue to secure checkout"}</button> : stripePromise ? <CheckoutFormProvider stripe={stripePromise} options={stripeOptions}><PaymentForm /></CheckoutFormProvider> : null}
        {error ? <p className="checkout-error" role="alert">{error}</p> : null}
      </div>
      <p className="checkout-terms">A temporary hold is placed when you complete checkout. Payment is captured after we verify availability.</p>
    </section>
    <aside className="order-summary" aria-labelledby="order-summary-title"><div className="order-summary-sticky"><div className="summary-heading"><h2 id="order-summary-title">Your bag</h2><Link href="/shop">Continue shopping</Link></div>
      <div className="summary-items">{items.map((item) => <article className="summary-item" key={`${item.productSlug}:${item.color}:${item.size}`}><div className="summary-image"><Image src={item.image} alt={item.alt} fill sizes="84px" /></div><div><h3>{item.name}</h3><p>{item.color} / {item.size}</p><div className="summary-quantity"><button onClick={() => updateQuantity(item.productSlug, item.color, item.size, item.quantity - 1)} disabled={started} type="button" aria-label={`Decrease ${item.name} quantity`}>−</button><output aria-live="polite">{item.quantity}</output><button onClick={() => updateQuantity(item.productSlug, item.color, item.size, item.quantity + 1)} disabled={started} type="button" aria-label={`Increase ${item.name} quantity`}>+</button></div><button className="summary-remove" disabled={started} onClick={() => removeItem(item.productSlug, item.color, item.size)} type="button">Remove</button></div><strong>{formatPrice(item.unitPrice * item.quantity)}</strong></article>)}</div>
      <dl className="summary-totals"><div><dt>Estimated subtotal</dt><dd>{formatPrice(subtotal)}</dd></div><div><dt>Estimated shipping</dt><dd>{shipping === 0 ? "Free" : formatPrice(shipping)}</dd></div><div><dt>Tax</dt><dd>Calculated at checkout</dd></div></dl><p className="summary-reassurance">Prices and the final total are confirmed in secure checkout.</p>
    </div></aside>
  </div>;
}
