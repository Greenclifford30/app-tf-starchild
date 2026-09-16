import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

export async function POST(request: Request) {
  return jsonResponse(await adminProductsRequest("/product-images/upload-url", { method: "POST", body: await request.text() }));
}
