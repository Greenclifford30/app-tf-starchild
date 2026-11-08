"use client";

import { useState } from "react";
import Link from "next/link";
import { useCart } from "../../cart";

type PurchasePanelProps = {
  productSlug: string;
  name: string;
  image: string;
  alt: string;
  price: number;
  colors: string[];
  sizes: string[];
  availability: "In stock" | "Limited availability";
};

export default function PurchasePanel({ productSlug, name, image, alt, price, colors, sizes, availability }: PurchasePanelProps) {
  const { addItem } = useCart();
  const [color, setColor] = useState(colors[0]);
  const [size, setSize] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [notice, setNotice] = useState<string | null>(null);
  const [added, setAdded] = useState(false);

  function addToBag() {
    if (!size) {
      setNotice("Choose a size before adding this piece to your bag.");
      setAdded(false);
      return;
    }

    addItem({ productSlug, name, image, alt, unitPrice: price, color, size, quantity });
    setNotice(`${name} in ${color}, size ${size}, is in your bag.`);
    setAdded(true);
  }

  return (
    <div className="product-purchase">
      <div className="product-price-row">
        <p className="product-price">${price.toFixed(2)}</p>
        <p className="product-availability">{availability}</p>
      </div>

      <fieldset className="product-option-group">
        <legend>Color <span>{color}</span></legend>
        <div className="product-option-list">
          {colors.map((option) => (
            <button
              className={`product-option product-color-option${color === option ? " is-selected" : ""}`}
              key={option}
              onClick={() => { setColor(option); setNotice(null); }}
              type="button"
              aria-pressed={color === option}
            >
              {option}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="product-option-group">
        <legend>Size <span>{size ?? "Select a size"}</span></legend>
        <div className="product-size-list">
          {sizes.map((option) => (
            <button
              className={`product-option product-size-option${size === option ? " is-selected" : ""}`}
              key={option}
              onClick={() => { setSize(option); setNotice(null); }}
              type="button"
              aria-pressed={size === option}
            >
              {option}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="product-quantity-row">
        <span id="quantity-label">Quantity</span>
        <div className="quantity-control" aria-labelledby="quantity-label">
          <button type="button" onClick={() => { setQuantity((current) => Math.max(1, current - 1)); setNotice(null); }} aria-label="Decrease quantity">−</button>
          <output aria-live="polite">{quantity}</output>
          <button type="button" onClick={() => { setQuantity((current) => Math.min(10, current + 1)); setNotice(null); }} aria-label="Increase quantity">+</button>
        </div>
      </div>

      <button className="button button-primary product-add-button" onClick={addToBag} type="button">
        Add to bag - ${(price * quantity).toFixed(2)}
      </button>
      <p className={`product-purchase-notice${notice ? " is-visible" : ""}`} aria-live="polite" role={notice ? "status" : undefined}>
        {notice}
      </p>
      {notice && added ? <Link className="text-link product-view-bag" href="/checkout">View bag</Link> : null}
      <p className="product-reassurance">Complimentary standard shipping on orders over $100. Returns accepted within 30 days.</p>
    </div>
  );
}
