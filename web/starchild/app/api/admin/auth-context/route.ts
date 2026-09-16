import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

export async function GET() {
  return jsonResponse(await adminProductsRequest("/admin/auth-context"));
}
