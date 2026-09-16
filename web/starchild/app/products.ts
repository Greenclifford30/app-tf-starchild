export type Product = {
  slug: string;
  category: string;
  name: string;
  image: string;
  alternateImage?: string;
  alt: string;
  homeSummary: string;
  story: string[];
  priceCents: number;
  colors: string[];
  sizes: string[];
  availability: "In stock" | "Limited availability";
  details: { label: string; value: string }[];
  featured: boolean;
  sortOrder: number;
};

type ProductListResponse = { products: Product[] };
type ProductResponse = { product: Product };

function apiUrl(path: string) {
  const base = process.env.PRODUCTS_API_URL;
  if (!base) throw new Error("PRODUCTS_API_URL is not configured.");
  return `${base.replace(/\/$/, "")}${path}`;
}

export async function getProducts(): Promise<Product[]> {
  const response = await fetch(apiUrl("/products"), { cache: "no-store" });
  if (!response.ok) throw new Error("Unable to load products.");
  return (await response.json() as ProductListResponse).products;
}

export async function getProduct(slug: string): Promise<Product | null> {
  const response = await fetch(apiUrl(`/products/${encodeURIComponent(slug)}`), { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("Unable to load product.");
  return (await response.json() as ProductResponse).product;
}
