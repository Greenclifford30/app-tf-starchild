"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

type NavigationItem = {
  href: string;
  label: string;
};

type MobileNavigationProps = {
  items: NavigationItem[];
};

export default function MobileNavigation({ items }: MobileNavigationProps) {
  const [isOpen, setIsOpen] = useState(false);
  const panelId = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setIsOpen(false);
      buttonRef.current?.focus();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen]);

  return (
    <div className="mobile-navigation">
      <button
        className="mobile-menu-button"
        type="button"
        ref={buttonRef}
        aria-controls={panelId}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <span aria-hidden="true">{isOpen ? "Close" : "Menu"}</span>
        <span className="sr-only">{isOpen ? "Close navigation menu" : "Open navigation menu"}</span>
      </button>
      {isOpen ? (
        <nav className="mobile-menu-panel" id={panelId} aria-label="Mobile navigation">
          {items.map((item) => (
            <Link href={item.href} key={item.href} onClick={() => setIsOpen(false)}>
              {item.label}
            </Link>
          ))}
        </nav>
      ) : null}
    </div>
  );
}
