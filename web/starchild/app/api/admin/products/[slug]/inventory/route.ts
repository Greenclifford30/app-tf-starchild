import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

export async function PUT(request: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return jsonResponse(await adminProductsRequest(`/products/${encodeURIComponent(slug)}/inventory`, { method: "PUT", body: await request.text() }));
}
