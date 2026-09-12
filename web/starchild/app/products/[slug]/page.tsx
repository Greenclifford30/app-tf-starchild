import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getProduct, products } from "../../products";
import PurchasePanel from "./purchase-panel";

type ProductPageProps = {
  params: Promise<{ slug: string }>;
};

export const dynamicParams = false;

export function generateStaticParams() {
  return products.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({ params }: ProductPageProps): Promise<Metadata> {
  const { slug } = await params;
  const product = getProduct(slug);

  if (!product) {
    return { title: "Product not found | Starchild Clothing" };
  }

  return {
    title: `${product.name} | Starchild Clothing`,
    description: product.homeSummary,
  };
}

export default async function ProductPage({ params }: ProductPageProps) {
  const { slug } = await params;
  const product = getProduct(slug);

  if (!product) {
    notFound();
  }

  return (
    <main className="product-page">
      <header className="product-page-header">
        <Link className="wordmark" href="/" aria-label="Starchild home">
          Starchild<span aria-hidden="true">*</span>
        </Link>
        <Link className="text-link" href="/shop">
          Back to collection
        </Link>
      </header>

      <section className="product-detail" aria-labelledby="product-title">
        <div className="product-gallery">
          <div className="product-detail-image media-frame">
            <Image src={product.image} alt={product.alt} fill priority sizes="(max-width: 899px) 100vw, 54vw" />
          </div>
          {product.alternateImage ? (
            <div className="product-detail-image media-frame">
              <Image src={product.alternateImage} alt="" fill sizes="(max-width: 899px) 100vw, 54vw" />
            </div>
          ) : null}
        </div>

        <article className="product-story">
          <p className="product-kind">{product.category}</p>
          <h1 id="product-title">{product.name}</h1>
          <p className="product-lede">{product.homeSummary}</p>
          <PurchasePanel
            productSlug={product.slug}
            name={product.name}
            image={product.image}
            alt={product.alt}
            price={product.price}
            colors={product.colors}
            sizes={product.sizes}
            availability={product.availability}
          />
          <div className="product-story-copy">
            {product.story.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
          <section className="product-details" aria-labelledby="product-details-title">
            <h2 id="product-details-title">The details</h2>
            <dl>
              {product.details.map((detail) => (
                <div key={detail.label}>
                  <dt>{detail.label}</dt>
                  <dd>{detail.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        </article>
      </section>
    </main>
  );
}
