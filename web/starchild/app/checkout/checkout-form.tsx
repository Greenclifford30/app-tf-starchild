"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";
import { useCart } from "../cart";

type OrderResponse = {
  orderReference?: string;
  message?: string;
};

function formatPrice(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);
}

function fieldValue(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

export default function CheckoutForm() {
  const { items, hydrated, subtotal, updateQuantity, removeItem, clearCart } = useCart();
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [orderNumber, setOrderNumber] = useState("");
  const [submissionId, setSubmissionId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const shipping = subtotal >= 100 ? 0 : 8;
  const total = subtotal + shipping;

  async function submitOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || !items.length) return;

    const form = event.currentTarget;
    if (!form.reportValidity()) return;

    const apiUrl = process.env.NEXT_PUBLIC_ORDERS_API_URL;
    if (!apiUrl) {
      setError("Order requests are temporarily unavailable. Please try again shortly.");
      return;
    }

    const formData = new FormData(form);
    const requestId = submissionId || crypto.randomUUID();
    if (!submissionId) setSubmissionId(requestId);

    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          submissionId: requestId,
          website: fieldValue(formData, "website"),
          customer: {
            email: fieldValue(formData, "email"),
            firstName: fieldValue(formData, "firstName"),
            lastName: fieldValue(formData, "lastName"),
            phone: fieldValue(formData, "phone"),
            address: fieldValue(formData, "address"),
            addressLine2: fieldValue(formData, "addressLine2"),
            city: fieldValue(formData, "city"),
            state: fieldValue(formData, "state"),
            postalCode: fieldValue(formData, "postalCode"),
            country: fieldValue(formData, "country"),
            notes: fieldValue(formData, "notes"),
          },
          items: items.map(({ productSlug, color, size, quantity }) => ({
            productSlug,
            color,
            size,
            quantity,
          })),
        }),
      });

      const result = await response.json().catch(() => ({})) as OrderResponse;
      if (!response.ok || !result.orderReference) {
        throw new Error(result.message || "We could not submit your order request. Please try again.");
      }

      setOrderNumber(result.orderReference);
      clearCart();
      setSubmitted(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not submit your order request. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <section className="order-confirmation" aria-labelledby="confirmation-title">
        <div className="confirmation-star" aria-hidden="true">*</div>
        <p className="eyebrow">Order request received</p>
        <h1 id="confirmation-title">You&apos;re in the orbit.</h1>
        <p className="confirmation-lede">Your order request <strong>{orderNumber}</strong> is with the Starchild team.</p>
        <div className="confirmation-steps">
          <p><span>01</span> We&apos;ll review availability and confirm your order.</p>
          <p><span>02</span> You&apos;ll receive payment instructions after confirmation.</p>
          <p><span>03</span> We&apos;ll share fulfillment details once everything is arranged.</p>
        </div>
        <p className="confirmation-note">This is not a payment receipt. Nothing has been charged today.</p>
        <Link className="button button-primary" href="/shop">Keep shopping</Link>
      </section>
    );
  }

  if (hydrated && items.length === 0) {
    return (
      <section className="checkout-empty" aria-labelledby="empty-bag-title">
        <p className="eyebrow">Your bag</p>
        <h1 id="empty-bag-title">Your orbit is empty.</h1>
        <p>Choose a piece and select its size before submitting an order request.</p>
        <Link className="button button-primary" href="/shop">Explore the collection</Link>
      </section>
    );
  }

  return (
    <div className="checkout-layout">
      <form className="checkout-form" onSubmit={submitOrder} aria-busy={submitting}>
        <div className="checkout-intro">
          <p className="eyebrow">Checkout</p>
          <h1>One step closer.</h1>
          <p>Submit your order request and we&apos;ll follow up with payment details once availability is confirmed.</p>
        </div>

        <fieldset className="checkout-section" disabled={submitting}>
          <legend><span>01</span> Contact</legend>
          <div className="form-grid">
            <label className="field field-full">Email address<input name="email" type="email" autoComplete="email" maxLength={254} required /></label>
            <label className="field">First name<input name="firstName" autoComplete="given-name" maxLength={80} required /></label>
            <label className="field">Last name<input name="lastName" autoComplete="family-name" maxLength={80} required /></label>
            <label className="field field-full">Phone number <em>For order updates</em><input name="phone" type="tel" autoComplete="tel" maxLength={30} required /></label>
          </div>
        </fieldset>

        <fieldset className="checkout-section" disabled={submitting}>
          <legend><span>02</span> Delivery</legend>
          <div className="form-grid">
            <label className="field field-full">Address<input name="address" autoComplete="street-address" maxLength={160} required /></label>
            <label className="field field-full">Apartment, suite, etc. <em>Optional</em><input name="addressLine2" autoComplete="address-line2" maxLength={100} /></label>
            <label className="field">City<input name="city" autoComplete="address-level2" maxLength={80} required /></label>
            <label className="field">State or province<input name="state" autoComplete="address-level1" maxLength={80} required /></label>
            <label className="field">Postal code<input name="postalCode" autoComplete="postal-code" maxLength={20} required /></label>
            <label className="field">Country<select name="country" autoComplete="country" defaultValue="US"><option value="US">United States</option><option value="CA">Canada</option></select></label>
            <label className="field field-full">Order notes <em>Optional</em><textarea name="notes" maxLength={500} rows={4} /></label>
          </div>
          <label className="shipping-choice"><input type="radio" name="shipping" value="standard" defaultChecked /><span><strong>Estimated standard shipping</strong><small>Final timing confirmed with your order</small></span><b>{shipping === 0 ? "Free" : formatPrice(shipping)}</b></label>
        </fieldset>

        <fieldset className="checkout-section checkout-payment-section" disabled={submitting}>
          <legend><span>03</span> Payment</legend>
          <div className="manual-payment-card">
            <p className="manual-payment-title">No payment is collected online</p>
            <p>After your request is submitted, Starchild Clothing will contact you to confirm availability, payment, shipping or pickup, and fulfillment.</p>
          </div>
        </fieldset>

        <div className="honeypot" aria-hidden="true"><label>Website<input name="website" tabIndex={-1} autoComplete="off" /></label></div>
        {error ? <p className="checkout-error" role="alert">{error}</p> : null}
        <button className="button button-primary checkout-submit" type="submit" disabled={!hydrated || submitting || !items.length}>
          {submitting ? "Submitting request…" : `Submit order request — ${formatPrice(total)}`}
        </button>
        <p className="checkout-terms">By submitting, you agree that Starchild may contact you about this order. Nothing will be charged until payment is arranged.</p>
      </form>

      <aside className="order-summary" aria-labelledby="order-summary-title">
        <div className="order-summary-sticky">
          <div className="summary-heading"><h2 id="order-summary-title">Your bag</h2><Link href="/shop">Continue shopping</Link></div>
          <div className="summary-items">
            {items.map((item) => (
              <article className="summary-item" key={`${item.productSlug}:${item.color}:${item.size}`}>
                <div className="summary-image"><Image src={item.image} alt={item.alt} fill sizes="84px" /></div>
                <div>
                  <h3>{item.name}</h3>
                  <p>{item.color} / {item.size}</p>
                  <div className="summary-quantity">
                    <button onClick={() => updateQuantity(item.productSlug, item.color, item.size, item.quantity - 1)} type="button" aria-label={`Decrease ${item.name} quantity`}>−</button>
                    <output aria-live="polite">{item.quantity}</output>
                    <button onClick={() => updateQuantity(item.productSlug, item.color, item.size, item.quantity + 1)} type="button" aria-label={`Increase ${item.name} quantity`}>+</button>
                  </div>
                  <button className="summary-remove" onClick={() => removeItem(item.productSlug, item.color, item.size)} type="button">Remove</button>
                </div>
                <strong>{formatPrice(item.unitPrice * item.quantity)}</strong>
              </article>
            ))}
          </div>
          <dl className="summary-totals"><div><dt>Subtotal</dt><dd>{formatPrice(subtotal)}</dd></div><div><dt>Estimated shipping</dt><dd>{shipping === 0 ? "Free" : formatPrice(shipping)}</dd></div><div className="summary-total"><dt>Estimated total</dt><dd>{formatPrice(total)}</dd></div></dl>
          <p className="summary-reassurance">Availability, shipping, and payment are confirmed personally after submission.</p>
        </div>
      </aside>
    </div>
  );
}
