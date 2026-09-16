import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

type RouteContext = { params: Promise<{ slug: string }> };

export async function PUT(request: Request, { params }: RouteContext) {
  const { slug } = await params;
  return jsonResponse(await adminProductsRequest(`/products/${encodeURIComponent(slug)}`, { method: "PUT", body: await request.text() }));
}

export async function DELETE(_request: Request, { params }: RouteContext) {
  const { slug } = await params;
  return jsonResponse(await adminProductsRequest(`/products/${encodeURIComponent(slug)}`, { method: "DELETE" }));
}
