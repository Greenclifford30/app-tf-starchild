import { adminProductsRequest, jsonResponse } from "@/app/admin/catalog-api";

type Context = { params: Promise<{ path: string[] }> };

async function proxy(request: Request, context: Context) {
  const { path } = await context.params;
  if (!path.length || !["orders", "order-requests"].includes(path[0]) || path.length > 3 || path.some((part) => !/^[a-zA-Z0-9-]+$/.test(part))) {
    return Response.json({ message: "Route not found." }, { status: 404 });
  }
  const search = new URL(request.url).search;
  const upstream = `/admin/${path.map(encodeURIComponent).join("/")}${search}`;
  return jsonResponse(await adminProductsRequest(upstream, {
    method: request.method,
    ...(request.method === "POST" ? { body: await request.text() } : {}),
  }));
}

export const GET = proxy;
export const POST = proxy;
