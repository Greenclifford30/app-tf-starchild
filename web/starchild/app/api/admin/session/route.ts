import { NextResponse } from "next/server";
import { ADMIN_TOKEN_COOKIE } from "@/app/admin/catalog-api";

export async function POST(request: Request) {
  const { email, password } = await request.json().catch(() => ({}));
  if (typeof email !== "string" || typeof password !== "string") {
    return NextResponse.json({ message: "Enter your email and password." }, { status: 400 });
  }

  const poolId = process.env.COGNITO_USER_POOL_ID;
  const clientId = process.env.COGNITO_USER_POOL_CLIENT_ID;
  const region = poolId?.split("_")[0];
  if (!poolId || !clientId || !region) {
    return NextResponse.json({ message: "Catalog sign-in has not been configured." }, { status: 503 });
  }

  const response = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "content-type": "application/x-amz-json-1.1",
      "x-amz-target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify({
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: clientId,
      AuthParameters: { USERNAME: email.trim(), PASSWORD: password },
    }),
  });
  const payload = await response.json().catch(() => ({}));
  const token = payload?.AuthenticationResult?.AccessToken;
  if (!response.ok || typeof token !== "string") {
    return NextResponse.json({ message: "We could not sign you in. Check your credentials and try again." }, { status: 401 });
  }

  const result = NextResponse.json({ ok: true });
  result.cookies.set(ADMIN_TOKEN_COOKIE, token, {
    httpOnly: true,
    maxAge: payload.AuthenticationResult.ExpiresIn ?? 3600,
    sameSite: "strict",
    secure: process.env.NODE_ENV === "production",
    path: "/",
  });
  return result;
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set(ADMIN_TOKEN_COOKIE, "", { httpOnly: true, maxAge: 0, path: "/" });
  return response;
}
