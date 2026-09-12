"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "starchild-cart-v1";
const MAX_ITEM_QUANTITY = 10;

export type CartItem = {
  productSlug: string;
  name: string;
  image: string;
  alt: string;
  color: string;
  size: string;
  quantity: number;
  unitPrice: number;
};

type AddCartItem = Omit<CartItem, "quantity"> & { quantity?: number };

type CartContextValue = {
  items: CartItem[];
  itemCount: number;
  subtotal: number;
  hydrated: boolean;
  addItem: (item: AddCartItem) => void;
  updateQuantity: (productSlug: string, color: string, size: string, quantity: number) => void;
  removeItem: (productSlug: string, color: string, size: string) => void;
  clearCart: () => void;
};

const CartContext = createContext<CartContextValue | null>(null);

function isCartItem(value: unknown): value is CartItem {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<CartItem>;
  return typeof item.productSlug === "string"
    && typeof item.name === "string"
    && typeof item.image === "string"
    && typeof item.alt === "string"
    && typeof item.color === "string"
    && typeof item.size === "string"
    && Number.isInteger(item.quantity)
    && Number(item.quantity) > 0
    && Number(item.quantity) <= MAX_ITEM_QUANTITY
    && typeof item.unitPrice === "number"
    && Number.isFinite(item.unitPrice)
    && item.unitPrice >= 0;
}

function sameVariant(item: CartItem, productSlug: string, color: string, size: string) {
  return item.productSlug === productSlug && item.color === color && item.size === size;
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    let active = true;
    let restoredItems: CartItem[] = [];
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed: unknown = JSON.parse(stored);
        if (Array.isArray(parsed)) restoredItems = parsed.filter(isCartItem);
      }
    } catch {
      window.localStorage.removeItem(STORAGE_KEY);
    }

    queueMicrotask(() => {
      if (!active) return;
      setItems(restoredItems);
      setHydrated(true);
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Keep the in-memory cart usable when browser storage is unavailable.
    }
  }, [hydrated, items]);

  const value = useMemo<CartContextValue>(() => ({
    items,
    hydrated,
    itemCount: items.reduce((total, item) => total + item.quantity, 0),
    subtotal: items.reduce((total, item) => total + item.unitPrice * item.quantity, 0),
    addItem(item) {
      const requestedQuantity = Math.min(MAX_ITEM_QUANTITY, Math.max(1, item.quantity ?? 1));
      setItems((current) => {
        const existing = current.find((candidate) => sameVariant(candidate, item.productSlug, item.color, item.size));
        if (!existing) return [...current, { ...item, quantity: requestedQuantity }];
        return current.map((candidate) => sameVariant(candidate, item.productSlug, item.color, item.size)
          ? { ...candidate, quantity: Math.min(MAX_ITEM_QUANTITY, candidate.quantity + requestedQuantity) }
          : candidate);
      });
    },
    updateQuantity(productSlug, color, size, quantity) {
      if (quantity <= 0) {
        setItems((current) => current.filter((item) => !sameVariant(item, productSlug, color, size)));
        return;
      }
      setItems((current) => current.map((item) => sameVariant(item, productSlug, color, size)
        ? { ...item, quantity: Math.min(MAX_ITEM_QUANTITY, Math.max(1, quantity)) }
        : item));
    },
    removeItem(productSlug, color, size) {
      setItems((current) => current.filter((item) => !sameVariant(item, productSlug, color, size)));
    },
    clearCart() {
      setItems([]);
    },
  }), [hydrated, items]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used within CartProvider");
  return context;
}
