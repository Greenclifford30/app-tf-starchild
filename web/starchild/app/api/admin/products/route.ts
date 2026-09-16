import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

export async function GET() {
  return jsonResponse(await adminProductsRequest("/admin/products"));
}

export async function POST(request: Request) {
  return jsonResponse(await adminProductsRequest("/products", { method: "POST", body: await request.text() }));
}
