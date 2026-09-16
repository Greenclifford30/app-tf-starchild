"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

type Detail = { label: string; value: string };
type CatalogProduct = {
  slug: string; name: string; category: string; image: string; imageKey: string; alternateImage?: string;
  alternateImageKey?: string; alt: string; homeSummary: string; story: string[]; priceCents: number;
  colors: string[]; sizes: string[]; availability: "In stock" | "Limited availability"; details: Detail[];
  featured: boolean; sortOrder: number; status: "ACTIVE" | "ARCHIVED";
};

type Draft = Omit<CatalogProduct, "image" | "alternateImage" | "status"> & { imageKey: string; alternateImageKey: string };

const blankDraft = (): Draft => ({
  slug: "", name: "", category: "", imageKey: "", alternateImageKey: "", alt: "", homeSummary: "", story: [""],
  priceCents: 0, colors: [""], sizes: [""], availability: "In stock", details: [{ label: "Material", value: "" }], featured: false, sortOrder: 0,
});

function productToDraft(product: CatalogProduct): Draft {
  const { image, alternateImage, status, ...draft } = product;
  return { ...draft, priceCents: product.priceCents / 100, alternateImageKey: product.alternateImageKey ?? "" };
}

function fieldList(value: string[]) { return value.map((item) => item.trim()).filter(Boolean); }

async function readJson(response: Response) {
  const payload = await response.json().catch(() => ({ message: "Something went wrong. Please try again." }));
  if (!response.ok) throw new Error(payload.message ?? "Something went wrong. Please try again.");
  return payload;
}

export default function CatalogManager() {
  const [products, setProducts] = useState<CatalogProduct[]>([]);
  const [draft, setDraft] = useState<Draft>(blankDraft);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [mode, setMode] = useState<"loading" | "signin" | "ready">("loading");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [challengeSession, setChallengeSession] = useState<string | null>(null);

  const activeProducts = useMemo(() => products.filter((product) => product.status === "ACTIVE"), [products]);
  const archivedProducts = useMemo(() => products.filter((product) => product.status === "ARCHIVED"), [products]);
  const selectedProduct = useMemo(() => products.find((product) => product.slug === selectedSlug) ?? null, [products, selectedSlug]);

  const loadProducts = useCallback(async (afterSignIn = false) => {
    setError("");
    const response = await fetch("/api/admin/products", { cache: "no-store" });
    if (response.status === 401 || response.status === 403) {
      setMode("signin");
      if (afterSignIn) setError("Cognito accepted the sign-in, but the catalog API rejected the token. Verify that the pool ID and app client ID in Amplify match the deployed API, then sign in again.");
      return false;
    }
    try {
      const payload = await readJson(response) as { products: CatalogProduct[] };
      setProducts(payload.products);
      setMode("ready");
      return true;
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to load the catalog."); setMode("ready"); }
  }, []);

  useEffect(() => { void loadProducts(); }, [loadProducts]);

  function beginNew() { setSelectedSlug(null); setDraft(blankDraft()); setError(""); setNotice(""); }
  function editProduct(product: CatalogProduct) { setSelectedSlug(product.slug); setDraft(productToDraft(product)); setError(""); setNotice(""); window.scrollTo({ top: 0, behavior: "smooth" }); }
  function update<K extends keyof Draft>(key: K, value: Draft[K]) { setDraft((current) => ({ ...current, [key]: value })); }
  function updateList(key: "story" | "colors" | "sizes", index: number, value: string) { setDraft((current) => ({ ...current, [key]: current[key].map((item, itemIndex) => itemIndex === index ? value : item) })); }
  function updateDetail(index: number, key: keyof Detail, value: string) { setDraft((current) => ({ ...current, details: current.details.map((detail, detailIndex) => detailIndex === index ? { ...detail, [key]: value } : detail) })); }

  async function uploadImage(file: File, target: "imageKey" | "alternateImageKey") {
    if (!file.type.match(/^image\/(jpeg|png|webp|avif)$/)) throw new Error("Use a JPG, PNG, WebP, or AVIF image.");
    const authorization = await fetch("/api/admin/products/upload", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ contentType: file.type }) });
    const upload = await readJson(authorization) as { key: string; uploadUrl: string };
    const result = await fetch(upload.uploadUrl, { method: "PUT", headers: { "content-type": file.type }, body: file });
    if (!result.ok) throw new Error("The image could not be uploaded. Please try again.");
    update(target, upload.key);
  }

  async function handleImage(file: File | undefined, target: "imageKey" | "alternateImageKey") {
    if (!file) return;
    setBusy(true); setError(""); setNotice("");
    try { await uploadImage(file, target); setNotice(target === "imageKey" ? "Primary image uploaded." : "Alternate image uploaded."); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to upload image."); }
    finally { setBusy(false); }
  }

  async function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError(""); setNotice("");
    const payload = {
      ...draft,
      priceCents: Math.round(draft.priceCents * 100),
      story: fieldList(draft.story), colors: fieldList(draft.colors), sizes: fieldList(draft.sizes),
      details: draft.details.filter((detail) => detail.label.trim() && detail.value.trim()),
      alternateImageKey: draft.alternateImageKey || null,
    };
    try {
      const isEditing = Boolean(selectedSlug);
      const response = await fetch(isEditing ? `/api/admin/products/${encodeURIComponent(selectedSlug!)}` : "/api/admin/products", {
        method: isEditing ? "PUT" : "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(payload),
      });
      const result = await readJson(response) as { product: CatalogProduct };
      setProducts((current) => isEditing ? current.map((product) => product.slug === result.product.slug ? result.product : product) : [...current, result.product]);
      setSelectedSlug(result.product.slug); setDraft(productToDraft(result.product));
      setNotice(isEditing ? "Product changes saved." : "Product added to the catalog.");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to save product."); }
    finally { setBusy(false); }
  }

  async function archiveProduct(product: CatalogProduct) {
    if (!window.confirm(`Archive ${product.name}? It will be removed from the storefront.`)) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const result = await readJson(await fetch(`/api/admin/products/${encodeURIComponent(product.slug)}`, { method: "DELETE" })) as { product: CatalogProduct };
      setProducts((current) => current.map((item) => item.slug === result.product.slug ? result.product : item));
      if (selectedSlug === product.slug) beginNew();
      setNotice(`${product.name} has been archived.`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to archive product."); }
    finally { setBusy(false); }
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const result = await readJson(await fetch("/api/admin/session", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(challengeSession ? { email, password, newPassword, session: challengeSession } : { email, password }) })) as { challenge?: string; session?: string };
      if (result.challenge === "NEW_PASSWORD_REQUIRED" && result.session) { setChallengeSession(result.session); setNewPassword(""); return; }
      setPassword(""); setNewPassword(""); setChallengeSession(null); await loadProducts(true);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign in."); }
    finally { setBusy(false); }
  }

  async function signOut() { await fetch("/api/admin/session", { method: "DELETE" }); beginNew(); setProducts([]); setMode("signin"); }

  if (mode === "loading") return <main className="catalog-loading" aria-busy="true"><div /><div /><div /></main>;
  if (mode === "signin") return <main className="catalog-login"><section><p className="catalog-kicker">Starchild / private</p><h1>Catalog manager</h1><p>{challengeSession ? "This account needs a permanent password before it can access the catalog." : "Sign in with the administrator account to update the collection."}</p>{error ? <p className="catalog-form-error" role="alert">{error}</p> : null}<form onSubmit={signIn}><label>Email<input type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required disabled={Boolean(challengeSession)} /></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>{challengeSession ? <label>New password<input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} minLength={8} required /></label> : null}<button className="button button-primary" disabled={busy}>{busy ? "Signing in…" : challengeSession ? "Set password" : "Sign in"}</button></form></section></main>;

  return <main className="catalog-page">
    <header className="catalog-header"><div><p className="catalog-kicker">Starchild / administration</p><h1>Catalog</h1></div><div className="catalog-header-actions"><a className="text-link" href="/shop" target="_blank" rel="noreferrer">View store</a><button className="catalog-quiet-button" type="button" onClick={() => void signOut()}>Sign out</button></div></header>
    <div className="catalog-layout">
      <aside className="catalog-sidebar"><button className="button button-primary catalog-new-button" type="button" onClick={beginNew}>Add product</button><div className="catalog-counts"><p><strong>{activeProducts.length}</strong> active</p><p><strong>{archivedProducts.length}</strong> archived</p></div><nav aria-label="Catalog products"><p className="catalog-list-heading">Live collection</p>{activeProducts.length ? activeProducts.map((product) => <button className={selectedSlug === product.slug ? "is-current" : ""} type="button" key={product.slug} onClick={() => editProduct(product)}><span>{product.name}</span><small>{product.category}</small></button>) : <p className="catalog-empty-list">No live products yet.</p>}{archivedProducts.length ? <><p className="catalog-list-heading catalog-archive-heading">Archived</p>{archivedProducts.map((product) => <button className={selectedSlug === product.slug ? "is-current" : ""} type="button" key={product.slug} onClick={() => editProduct(product)}><span>{product.name}</span><small>Archived</small></button>)}</> : null}</nav></aside>
      <section className="catalog-editor"><div className="catalog-editor-heading"><div><p className="catalog-kicker">{selectedProduct ? "Editing product" : "New product"}</p><h2>{selectedProduct ? selectedProduct.name : "Add a product"}</h2></div>{selectedProduct?.status === "ACTIVE" ? <button className="catalog-archive-button" type="button" onClick={() => void archiveProduct(selectedProduct)} disabled={busy}>Archive</button> : null}</div>
      <p className="catalog-editor-intro">Complete the details below. Fields marked required are shown on the storefront.</p>{notice ? <p className="catalog-notice" role="status">{notice}</p> : null}{error ? <p className="catalog-form-error" role="alert">{error}</p> : null}
      <form className="catalog-form" onSubmit={saveProduct}>
        <fieldset><legend>Product basics</legend><div className="catalog-form-grid"><label>Product name<input value={draft.name} onChange={(event) => update("name", event.target.value)} maxLength={160} required /></label><label>Category<input value={draft.category} onChange={(event) => update("category", event.target.value)} maxLength={80} required /></label><label>URL slug<input value={draft.slug} onChange={(event) => update("slug", event.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))} pattern="[a-z0-9]+(-[a-z0-9]+)*" disabled={Boolean(selectedSlug)} required /><small>Lowercase letters, numbers, and hyphens only.</small></label><label>Price (USD)<input type="number" inputMode="decimal" min="0.01" max="10000" step="0.01" value={draft.priceCents || ""} onChange={(event) => update("priceCents", Number(event.target.value))} required /></label><label>Catalog order<input type="number" min="0" max="1000000" step="1" value={draft.sortOrder} onChange={(event) => update("sortOrder", Number(event.target.value))} required /><small>Lower numbers appear first.</small></label><label>Availability<select value={draft.availability} onChange={(event) => update("availability", event.target.value as Draft["availability"])}><option>In stock</option><option>Limited availability</option></select></label></div><label className="catalog-field-full">Short storefront summary<textarea value={draft.homeSummary} onChange={(event) => update("homeSummary", event.target.value)} maxLength={300} required /></label><label className="catalog-field-full">Image description<input value={draft.alt} onChange={(event) => update("alt", event.target.value)} maxLength={500} required /><small>Describe the product image for customers using screen readers.</small></label></fieldset>
        <fieldset><legend>Images</legend><p className="catalog-field-description">Upload a primary image. The alternate image appears on hover where supported.</p><div className="catalog-image-grid"><label className="catalog-image-field">Primary image<input type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={(event) => void handleImage(event.target.files?.[0], "imageKey")} /><span>{draft.imageKey ? "Replace primary image" : "Upload primary image"}</span>{draft.imageKey ? <small>{draft.imageKey}</small> : null}</label><label className="catalog-image-field">Alternate image <em>optional</em><input type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={(event) => void handleImage(event.target.files?.[0], "alternateImageKey")} /><span>{draft.alternateImageKey ? "Replace alternate image" : "Upload alternate image"}</span>{draft.alternateImageKey ? <small>{draft.alternateImageKey}</small> : null}</label></div></fieldset>
        <fieldset><legend>Variants</legend><div className="catalog-repeat-grid"><Repeater label="Colors" values={draft.colors} onChange={(index, value) => updateList("colors", index, value)} onAdd={() => update("colors", [...draft.colors, ""])} onRemove={(index) => update("colors", draft.colors.filter((_, itemIndex) => itemIndex !== index))} /><Repeater label="Sizes" values={draft.sizes} onChange={(index, value) => updateList("sizes", index, value)} onAdd={() => update("sizes", [...draft.sizes, ""])} onRemove={(index) => update("sizes", draft.sizes.filter((_, itemIndex) => itemIndex !== index))} /></div></fieldset>
        <fieldset><legend>Product story</legend><p className="catalog-field-description">Each paragraph is shown in the product detail page.</p><Repeater label="Story paragraphs" values={draft.story} multiline onChange={(index, value) => updateList("story", index, value)} onAdd={() => update("story", [...draft.story, ""])} onRemove={(index) => update("story", draft.story.filter((_, itemIndex) => itemIndex !== index))} /><label className="catalog-checkbox"><input type="checkbox" checked={draft.featured} onChange={(event) => update("featured", event.target.checked)} /> Feature on the home page</label></fieldset>
        <fieldset><legend>Product details</legend><div className="catalog-details">{draft.details.map((detail, index) => <div key={`${index}-${detail.label}`}><label>Label<input value={detail.label} onChange={(event) => updateDetail(index, "label", event.target.value)} required /></label><label>Value<input value={detail.value} onChange={(event) => updateDetail(index, "value", event.target.value)} required /></label>{draft.details.length > 1 ? <button type="button" className="catalog-remove" onClick={() => update("details", draft.details.filter((_, detailIndex) => detailIndex !== index))}>Remove</button> : null}</div>)}</div><button type="button" className="catalog-add-row" onClick={() => update("details", [...draft.details, { label: "", value: "" }])}>Add detail</button></fieldset>
        <div className="catalog-save-row"><button className="button button-primary" disabled={busy}>{busy ? "Saving…" : selectedSlug ? "Save changes" : "Add product"}</button>{selectedSlug ? <button className="button button-secondary" type="button" onClick={beginNew} disabled={busy}>Create another</button> : null}</div>
      </form></section>
    </div>
  </main>;
}

function Repeater({ label, values, multiline = false, onChange, onAdd, onRemove }: { label: string; values: string[]; multiline?: boolean; onChange: (index: number, value: string) => void; onAdd: () => void; onRemove: (index: number) => void }) {
  return <div className="catalog-repeater"><p>{label}</p>{values.map((value, index) => <div key={index}>{multiline ? <textarea aria-label={`${label} ${index + 1}`} value={value} onChange={(event) => onChange(index, event.target.value)} required /> : <input aria-label={`${label} ${index + 1}`} value={value} onChange={(event) => onChange(index, event.target.value)} required />}{values.length > 1 ? <button type="button" className="catalog-remove" onClick={() => onRemove(index)}>Remove</button> : null}</div>)}<button type="button" className="catalog-add-row" onClick={onAdd}>Add {label.slice(0, -1)}</button></div>;
}
