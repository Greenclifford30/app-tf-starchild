"use client";

import Image from "next/image";
import Link from "next/link";
import { useMemo, useState } from "react";
import type { Product } from "../products";

type ShopCatalogProps = { products: Product[] };

const availability = ["All availability", "In stock", "Limited availability"] as const;

export default function ShopCatalog({ products }: ShopCatalogProps) {
  const categories = useMemo(() => ["All pieces", ...Array.from(new Set(products.map((product) => product.category)))], [products]);
  const [category, setCategory] = useState("All pieces");
  const [stockStatus, setStockStatus] = useState<(typeof availability)[number]>("All availability");

  const filteredProducts = useMemo(
    () => products.filter((product) =>
      (category === "All pieces" || product.category === category)
      && (stockStatus === "All availability" || product.availability === stockStatus),
    ),
    [category, products, stockStatus],
  );

  return (
    <section className="shop-collection" id="collection" aria-label="All Starchild products">
      <div className="shop-toolbar">
        <p className="shop-count" aria-live="polite">{filteredProducts.length} {filteredProducts.length === 1 ? "piece" : "pieces"}</p>
        <div className="shop-filters">
          <label>
            <span>Category</span>
            <select value={category} onChange={(event) => setCategory(event.target.value as typeof category)}>
              {categories.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label>
            <span>Availability</span>
            <select value={stockStatus} onChange={(event) => setStockStatus(event.target.value as typeof stockStatus)}>
              {availability.map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
        </div>
      </div>

      {filteredProducts.length ? (
        <div className="shop-product-grid">
          {filteredProducts.map((product) => (
            <article className="shop-product-card" key={product.slug}>
              <Link className="shop-product-image media-frame" href={`/products/${product.slug}`} aria-label={`View ${product.name}`}>
                <Image className="product-image-primary" src={product.image} alt={product.alt} fill sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, 25vw" />
                {product.alternateImage ? <Image className="product-image-alternate" src={product.alternateImage} alt="" fill sizes="(max-width: 639px) 50vw, (max-width: 1023px) 33vw, 25vw" /> : null}
                {product.availability === "Limited availability" ? <span className="product-status">Limited</span> : null}
              </Link>
              <div className="shop-product-info">
                <div>
                  <p className="product-kind">{product.category}</p>
                  <h2><Link href={`/products/${product.slug}`}>{product.name}</Link></h2>
                </div>
                <p className="shop-product-price">${(product.priceCents / 100).toFixed(2)}</p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="shop-empty" role="status">
          <p className="eyebrow">Nothing here yet</p>
          <h2>That filter combination is taking the scenic route.</h2>
          <button className="text-link" type="button" onClick={() => { setCategory("All pieces"); setStockStatus("All availability"); }}>Show all pieces</button>
        </div>
      )}
    </section>
  );
}
