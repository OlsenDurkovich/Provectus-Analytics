// localStorage helpers for auth state. Centralized so we never typo the key.
//
// We persist both tokens and the user object because the user object lets us
// render the shell synchronously on first paint without a /me round-trip.

export type StoredUser = {
  user_id: number;
  email: string;
  role: string;
  is_active: boolean;
};

const KEY_ACCESS = 'pv_auth_access';
const KEY_REFRESH = 'pv_auth_refresh';
const KEY_USER = 'pv_auth_user';

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(KEY_REFRESH);
}

export function getStoredUser(): StoredUser | null {
  const raw = localStorage.getItem(KEY_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

export function setAuth(access: string, refresh: string, user?: StoredUser | null): void {
  localStorage.setItem(KEY_ACCESS, access);
  localStorage.setItem(KEY_REFRESH, refresh);
  if (user) localStorage.setItem(KEY_USER, JSON.stringify(user));
}

export function setStoredUser(user: StoredUser): void {
  localStorage.setItem(KEY_USER, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(KEY_ACCESS);
  localStorage.removeItem(KEY_REFRESH);
  localStorage.removeItem(KEY_USER);
}
