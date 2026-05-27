// Token-aware fetch wrapper.
//
// - Reads the access token from localStorage and attaches it as Bearer.
// - On 401, tries one refresh round-trip with the stored refresh token; if that
//   works, retries the original request once. On the second 401 (or any failure
//   to refresh), it dispatches a custom 'pv:auth-expired' event so the
//   AuthContext can sign the user out + bounce to /login.
//
// Only auth-aware code paths use this; /api/auth/login and /api/auth/refresh
// still hit fetch directly (the wrapper would deadlock on them).

import { clearAuth, getAccessToken, getRefreshToken, setAuth } from './storage';

const AUTH_EXPIRED_EVENT = 'pv:auth-expired';

export function onAuthExpired(handler: () => void): () => void {
  const wrapped = () => handler();
  window.addEventListener(AUTH_EXPIRED_EVENT, wrapped);
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, wrapped);
}

function signalExpired(): void {
  clearAuth();
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

async function attemptRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const body = (await res.json()) as { access_token: string; refresh_token: string };
    setAuth(body.access_token, body.refresh_token);
    return true;
  } catch {
    return false;
  }
}

function withAuth(init: RequestInit | undefined, token: string | null): RequestInit {
  const headers = new Headers(init?.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return { ...init, headers };
}

export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getAccessToken();
  let res = await fetch(input, withAuth(init, token));
  if (res.status !== 401) return res;

  const refreshed = await attemptRefresh();
  if (!refreshed) {
    signalExpired();
    return res;
  }
  const newToken = getAccessToken();
  res = await fetch(input, withAuth(init, newToken));
  if (res.status === 401) signalExpired();
  return res;
}
