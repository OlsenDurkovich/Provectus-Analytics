// AuthContext — single source of truth for auth state on the frontend.
//
// Flow:
//   - On mount, hydrate from localStorage (the persisted user + tokens).
//   - Render synchronously: if a persisted user exists, treat the app as
//     authenticated immediately. In the background, validate the token by
//     calling /api/auth/me; if that 401s, sign out.
//   - login(): POST /api/auth/login, persist tokens + user, update state.
//   - logout(): POST /api/auth/logout (best effort), clear state.
//
// The authFetch wrapper handles silent refresh; it also dispatches a
// 'pv:auth-expired' event when refresh fails. We subscribe here to sign out.

import {
  createContext, useCallback, useContext, useEffect, useMemo, useRef, useState,
  type ReactNode,
} from 'react';
import { authFetch, onAuthExpired } from './authFetch';
import {
  clearAuth, getAccessToken, getStoredUser, setAuth, setStoredUser,
  type StoredUser,
} from './storage';

type AuthStatus = 'authenticated' | 'unauthenticated';

type AuthContextValue = {
  user: StoredUser | null;
  status: AuthStatus;
  isAdmin: boolean;
  canSee: (page: string) => boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export class LoginFailure extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'LoginFailure';
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<StoredUser | null>(() => getStoredUser());
  const [status, setStatusState] = useState<AuthStatus>(() =>
    getStoredUser() && getAccessToken() ? 'authenticated' : 'unauthenticated',
  );
  const validatedRef = useRef(false);

  const signOutLocal = useCallback(() => {
    clearAuth();
    setUser(null);
    setStatusState('unauthenticated');
  }, []);

  // Background revalidation on first mount (with a persisted session).
  useEffect(() => {
    if (validatedRef.current) return;
    if (status !== 'authenticated') return;
    validatedRef.current = true;
    (async () => {
      try {
        const res = await authFetch('/api/auth/me');
        if (!res.ok) {
          signOutLocal();
          return;
        }
        const fresh = (await res.json()) as StoredUser;
        setStoredUser(fresh);
        setUser(fresh);
      } catch {
        // Network glitch — leave the cached session in place; authFetch will
        // catch real auth failures on subsequent API calls.
      }
    })();
  }, [status, signOutLocal]);

  // Subscribe to global auth-expired events from authFetch.
  useEffect(() => onAuthExpired(signOutLocal), [signOutLocal]);

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => '');
      throw new LoginFailure(res.status, detail || `Login failed (${res.status})`);
    }
    const body = (await res.json()) as { access_token: string; refresh_token: string };
    setAuth(body.access_token, body.refresh_token);

    // Fetch the user so the topbar can show role/email immediately.
    const meRes = await authFetch('/api/auth/me');
    if (!meRes.ok) {
      throw new LoginFailure(meRes.status, 'Authentication succeeded but /me failed');
    }
    const me = (await meRes.json()) as StoredUser;
    setStoredUser(me);
    setUser(me);
    setStatusState('authenticated');
  }, []);

  const logout = useCallback(async () => {
    try {
      await authFetch('/api/auth/logout', { method: 'POST' });
    } catch {
      // Even if the network call fails, drop local state.
    }
    signOutLocal();
  }, [signOutLocal]);

  const value = useMemo(() => {
    const isAdmin = user?.is_admin ?? false;
    const canSee = (page: string) => isAdmin || (user?.pages?.includes(page) ?? false);
    return { user, status, isAdmin, canSee, login, logout };
  }, [user, status, login, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
