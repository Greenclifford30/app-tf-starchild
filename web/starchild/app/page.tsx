import Image from "next/image";
import Link from "next/link";
import BagLink from "./bag-link";
import BrandLogo from "./brand-logo";
import MobileNavigation from "./mobile-navigation";
import { featuredProducts } from "./products";

const primaryNavigation = [
  { href: "/shop", label: "Shop" },
  { href: "#new-arrivals", label: "New arrivals" },
  { href: "#story", label: "Our story" },
  { href: "#community", label: "Community" },
];

export default function Home() {
  return (
    <div className="site-shell">
      <div className="announcement">Complimentary standard shipping on orders over $100.</div>

      <header className="site-header">
        <Link className="wordmark" href="/" aria-label="Starchild home">
          <BrandLogo />
        </Link>

        <nav className="main-nav" aria-label="Main navigation">
          <Link href="/shop">Shop</Link>
          <a href="#new-arrivals">New arrivals</a>
          <a href="#story">Our story</a>
          <a href="#community">Community</a>
        </nav>

        <div className="utility-nav">
          <BagLink />
          <MobileNavigation items={primaryNavigation} />
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <p className="eyebrow">The late summer edit</p>
            <h1 id="hero-title">Clothes for the way you move.</h1>
            <p className="hero-summary">
              Everyday pieces with a clearer point of view, designed to stay in rotation.
            </p>
            <Link className="button button-primary" href="/shop">
              Shop new arrivals
            </Link>
          </div>

          <div className="hero-media">
            <Image
              src="/products/love_in_motion_hoodie.PNG"
              alt="Black Straight to the Heart hoodie with a cupid graphic"
              fill
              priority
              sizes="(max-width: 767px) 100vw, 58vw"
            />
          </div>
        </section>

        <section className="arrivals" id="new-arrivals" aria-labelledby="arrivals-title">
          <div className="section-heading arrivals-heading">
            <p className="eyebrow">New arrivals</p>
            <h2 id="arrivals-title">The daily uniform, reconsidered.</h2>
          </div>

          <div className="product-grid">
            {featuredProducts.map((product) => (
              <article className="product-card" key={product.name}>
                <Link className="product-image-link" href={`/products/${product.slug}`} aria-label={`View ${product.name}`}>
                  <div className="product-image media-frame">
                    <Image
                      className="product-image-primary"
                      src={product.image}
                      alt={product.alt}
                      fill
                      sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, 25vw"
                    />
                    {product.alternateImage ? (
                      <Image
                        className="product-image-alternate"
                        src={product.alternateImage}
                        alt=""
                        fill
                        sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, 25vw"
                      />
                    ) : null}
                  </div>
                </Link>
                <div className="product-card-details">
                  <div>
                    <p className="product-kind">{product.category}</p>
                    <h3><Link href={`/products/${product.slug}`}>{product.name}</Link></h3>
                    <p className="product-summary">{product.homeSummary}</p>
                  </div>
                  <Link className="text-link product-card-link" href={`/products/${product.slug}`}>
                    View piece
                  </Link>
                </div>
              </article>
            ))}
          </div>
          <Link className="text-link arrivals-shop-link" href="/shop">
            See the full collection
          </Link>
        </section>

        <section className="story" id="story" aria-labelledby="story-title">
          <div className="story-copy">
            <h2 id="story-title">A good piece earns its place.</h2>
            <p>
              We begin with versatile silhouettes, thoughtful fabrics, and finishing details that make everyday dressing feel considered.
            </p>
            <a className="text-link" href="#impact">
              How we make it
            </a>
          </div>

          <div className="story-media media-frame">
            <Image
              src="/products/call_unto_him_crewneck.png"
              alt="Call Unto Him Starchild crewneck"
              fill
              sizes="(max-width: 767px) 100vw, 42vw"
            />
          </div>

          <div className="story-note" id="impact">
            <span className="star-mark" aria-hidden="true">*</span>
            <p>
              Clear material, maker, and care details belong with every piece. Better choices need useful information.
            </p>
          </div>
        </section>

        <section className="community" id="community" aria-labelledby="community-title">
          <div className="community-media community-brand-panel">
            <div className="community-logo-wrap">
              <BrandLogo className="community-logo" decorative={false} />
              <p>Made to move with you.</p>
            </div>
            <div className="community-product-frame">
              <Image
                src="/products/starchild_juneteenth_shirt.png"
                alt="Starchild Juneteenth T-shirt"
                fill
                sizes="(max-width: 767px) 72vw, 36vw"
              />
            </div>
          </div>
          <div className="community-intro">
            <h2 id="community-title">A shared point of view.</h2>
            <p>Tag your look for a chance to appear in the Starchild community edit.</p>
            <Link className="button button-secondary" href="/shop">Explore the collection</Link>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="footer-top">
          <Link className="wordmark" href="/" aria-label="Back to Starchild home">
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
    </div>
  );
}
