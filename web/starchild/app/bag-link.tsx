"use client";

import Link from "next/link";
import { useCart } from "./cart";

export default function BagLink() {
  const { hydrated, itemCount } = useCart();
  const count = hydrated ? itemCount : 0;

  return (
    <Link className="bag-link" href="/checkout">
      Bag <span aria-label={`${count} ${count === 1 ? "item" : "items"}`}>{count}</span>
    </Link>
  );
}
