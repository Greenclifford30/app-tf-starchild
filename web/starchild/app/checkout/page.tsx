import type { Metadata } from "next";
import Link from "next/link";
import BrandLogo from "../brand-logo";
import CheckoutForm from "./checkout-form";

export const metadata: Metadata = {
  title: "Checkout | Starchild Clothing",
  description: "Submit a Starchild order request and receive manual payment details.",
};

export default function CheckoutPage() {
  return (
    <main className="checkout-page">
      <header className="checkout-header">
        <Link className="wordmark" href="/" aria-label="Starchild home">
          <BrandLogo />
        </Link>
        <p className="checkout-secure-note"><span aria-hidden="true">●</span> Secure order request</p>
      </header>
      <CheckoutForm />
    </main>
  );
}
