// Auth-state storage. Centralized so we never typo a key.
//
// "Remember me" controls WHERE the session lives:
//   - remembered  → localStorage  (survives closing the browser)
//   - not remembered → sessionStorage (cleared when the tab/browser closes —
//     safer on shared machines)
//
// Reads check localStorage first, then sessionStorage, so the rest of the app
// doesn't care which one holds the session. Token refreshes (which don't know
// the original choice) write back to wherever the session currently lives.

export type StoredUser = {
  user_id: number;
  email: string;
  role: string;
  is_active: boolean;
  pages: string[];
  is_admin: boolean;
  student_id?: number | null;
};

const KEY_ACCESS = 'pv_auth_access';
const KEY_REFRESH = 'pv_auth_refresh';
const KEY_USER = 'pv_auth_user';

// Where the session currently lives. sessionStorage wins if it holds a token
// (a "not remembered" login); otherwise localStorage (remembered, or empty).
function activeStorage(): Storage {
  return sessionStorage.getItem(KEY_ACCESS) !== null ? sessionStorage : localStorage;
}

function readKey(key: string): string | null {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key);
}

export function getAccessToken(): string | null {
  return readKey(KEY_ACCESS);
}

export function getRefreshToken(): string | null {
  return readKey(KEY_REFRESH);
}

export function getStoredUser(): StoredUser | null {
  const raw = readKey(KEY_USER);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

// At login, pass `remember` to pick the storage. On refresh, omit it to keep
// the session in whichever storage it already occupies.
export function setAuth(access: string, refresh: string, remember?: boolean): void {
  let store: Storage;
  if (remember === undefined) {
    store = activeStorage();
  } else {
    // Explicit choice: clear any prior session from BOTH stores first so a
    // stale token in the other one can't shadow this one.
    clearAuth();
    store = remember ? localStorage : sessionStorage;
  }
  store.setItem(KEY_ACCESS, access);
  store.setItem(KEY_REFRESH, refresh);
}

export function setStoredUser(user: StoredUser): void {
  activeStorage().setItem(KEY_USER, JSON.stringify(user));
}

export function clearAuth(): void {
  for (const store of [localStorage, sessionStorage]) {
    store.removeItem(KEY_ACCESS);
    store.removeItem(KEY_REFRESH);
    store.removeItem(KEY_USER);
  }
}
