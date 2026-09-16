import { NextResponse } from "next/server";
import { ADMIN_TOKEN_COOKIE } from "@/app/admin/catalog-api";

export async function POST(request: Request) {
  const { email, password, newPassword, session } = await request.json().catch(() => ({}));
  if (typeof email !== "string" || typeof password !== "string") {
    return NextResponse.json({ message: "Enter your email and password." }, { status: 400 });
  }

  const poolId = process.env.COGNITO_USER_POOL_ID;
  const clientId = process.env.COGNITO_USER_POOL_CLIENT_ID;
  const region = poolId?.split("_")[0];
  if (!poolId || !clientId || !region) {
    return NextResponse.json({ message: "Catalog sign-in has not been configured." }, { status: 503 });
  }

  const isPasswordChallenge = typeof newPassword === "string" && typeof session === "string";
  const response = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
    method: "POST",
    headers: {
      "content-type": "application/x-amz-json-1.1",
      "x-amz-target": isPasswordChallenge
        ? "AWSCognitoIdentityProviderService.RespondToAuthChallenge"
        : "AWSCognitoIdentityProviderService.InitiateAuth",
    },
    body: JSON.stringify(isPasswordChallenge ? {
      ChallengeName: "NEW_PASSWORD_REQUIRED",
      ClientId: clientId,
      Session: session,
      ChallengeResponses: { USERNAME: email.trim(), NEW_PASSWORD: newPassword },
    } : {
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: clientId,
      AuthParameters: { USERNAME: email.trim(), PASSWORD: password },
    }),
  });
  const payload = await response.json().catch(() => ({}));
  if (response.ok && payload?.ChallengeName === "NEW_PASSWORD_REQUIRED" && typeof payload?.Session === "string") {
    return NextResponse.json({ challenge: "NEW_PASSWORD_REQUIRED", session: payload.Session });
  }
  const token = payload?.AuthenticationResult?.AccessToken;
  if (!response.ok || typeof token !== "string") {
    const errorType = typeof payload?.__type === "string" ? payload.__type.split("#").pop() ?? "" : "";
    const errorMessages: Record<string, string> = {
      UserNotFoundException: "This account was not found in the configured Cognito user pool.",
      UserNotConfirmedException: "Confirm this account in Cognito before signing in.",
      PasswordResetRequiredException: "This account needs a password reset in Cognito before it can sign in.",
      InvalidParameterException: "The Cognito app client is not configured for password sign-in.",
    };
    const errorMessage = errorMessages[errorType] ?? "We could not sign you in. Check your credentials and try again.";
    return NextResponse.json({ message: errorMessage }, { status: 401 });
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
