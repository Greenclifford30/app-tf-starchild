import type { Metadata } from "next";
import Link from "next/link";
import { products } from "../products";
import ShopCatalog from "./shop-catalog";
import BagLink from "../bag-link";
import BrandLogo from "../brand-logo";
import MobileNavigation from "../mobile-navigation";

const shopNavigation = [
  { href: "/shop", label: "Shop all" },
  { href: "/#new-arrivals", label: "New arrivals" },
  { href: "/#story", label: "Our story" },
  { href: "/#community", label: "Community" },
];

export const metadata: Metadata = {
  title: "Shop All | Starchild Clothing",
  description: "Explore every Starchild piece, made for the way you move.",
};

export default function ShopPage() {
  return (
    <main className="shop-page">
      <div className="announcement">Complimentary standard shipping on orders over $100.</div>

      <header className="shop-header">
        <Link className="wordmark" href="/" aria-label="Starchild home">
          <BrandLogo />
        </Link>
        <nav className="shop-nav" aria-label="Shop navigation">
          <Link href="/shop" aria-current="page">Shop all</Link>
          <Link href="/#new-arrivals">New arrivals</Link>
          <Link href="/#story">Our story</Link>
        </nav>
        <div className="utility-nav">
          <a href="#collection">Collection</a>
          <BagLink />
          <MobileNavigation items={shopNavigation} />
        </div>
      </header>

      <section className="shop-intro" aria-labelledby="shop-title">
        <p className="eyebrow">Starchild collection</p>
        <h1 id="shop-title">Find your orbit.</h1>
        <p>All the pieces, each made to carry a little more meaning through your everyday.</p>
        <span className="shop-star" aria-hidden="true">*</span>
      </section>

      <ShopCatalog products={products} />

      <footer className="site-footer shop-footer">
        <div className="footer-top">
          <Link className="wordmark" href="/" aria-label="Starchild home">
            <BrandLogo />
          </Link>
          <p>Thoughtful clothing for an everyday orbit.</p>
        </div>
        <div className="footer-links">
          <Link href="/shop">Shop</Link>
          <Link href="/checkout">Order request</Link>
        </div>
        <p className="copyright">© 2026 Starchild Clothing</p>
      </footer>
    </main>
  );
}
