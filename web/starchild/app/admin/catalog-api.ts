import { cookies } from "next/headers";

export const ADMIN_TOKEN_COOKIE = "starchild_admin_token";

function productsApiUrl(path: string) {
  const base = process.env.PRODUCTS_API_URL;
  if (!base) throw new Error("PRODUCTS_API_URL is not configured.");
  return `${base.replace(/\/$/, "")}${path}`;
}

export async function adminProductsRequest(path: string, init: RequestInit = {}) {
  const token = (await cookies()).get(ADMIN_TOKEN_COOKIE)?.value;
  if (!token) return new Response(JSON.stringify({ message: "Sign in is required." }), { status: 401 });

  return fetch(productsApiUrl(path), {
    ...init,
    cache: "no-store",
    headers: {
      authorization: `Bearer ${token}`,
      "content-type": "application/json",
      ...(init.headers ?? {}),
    },
  });
}

export async function jsonResponse(response: Response) {
  const payload = await response.json().catch(() => ({ message: "The catalog service returned an invalid response." }));
  return Response.json(payload, { status: response.status });
}
