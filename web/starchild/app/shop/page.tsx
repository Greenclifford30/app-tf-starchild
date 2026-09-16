import type { Metadata } from "next";
import Link from "next/link";
import { getProducts } from "../products";
import ShopCatalog from "./shop-catalog";
import BagLink from "../bag-link";
import BrandLogo from "../brand-logo";
import MobileNavigation from "../mobile-navigation";

export const dynamic = "force-dynamic";

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

export default async function ShopPage() {
  const products = await getProducts();
  return (
    <main className="shop-page">
      <div className="announcement">Complimentary standard shipping on orders over $100.</div>

      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="Starchild home">
          <BrandLogo />
        </Link>
        <nav className="main-nav" aria-label="Main navigation">
          <Link href="/shop" aria-current="page">Shop</Link>
          <Link href="/#new-arrivals">New arrivals</Link>
          <Link href="/#story">Our story</Link>
          <Link href="/#community">Community</Link>
        </nav>
        <div className="utility-nav">
          <BagLink />
          <MobileNavigation items={shopNavigation} />
        </div>
      </header>

      <section className="shop-intro" aria-labelledby="shop-title">
        <div className="shop-intro-title">
          <p className="eyebrow">Starchild collection</p>
          <h1 id="shop-title">Find your orbit.</h1>
        </div>
        <p className="shop-intro-summary">All the pieces, each made to carry a little more meaning through your everyday.</p>
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
