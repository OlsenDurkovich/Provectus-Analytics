import { beforeEach, expect, test } from 'vitest';
import {
  clearAuth, getAccessToken, getRefreshToken, setAuth, setStoredUser, getStoredUser,
} from './storage';

const A = 'pv_auth_access';

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

test('remember=true stores tokens in localStorage only', () => {
  setAuth('acc', 'ref', true);
  expect(localStorage.getItem(A)).toBe('acc');
  expect(sessionStorage.getItem(A)).toBeNull();
  expect(getAccessToken()).toBe('acc');
  expect(getRefreshToken()).toBe('ref');
});

test('remember=false stores tokens in sessionStorage only', () => {
  setAuth('acc', 'ref', false);
  expect(sessionStorage.getItem(A)).toBe('acc');
  expect(localStorage.getItem(A)).toBeNull();
  expect(getAccessToken()).toBe('acc');
});

test('switching remember clears the other store (no stale shadow)', () => {
  setAuth('old', 'oldref', true); // localStorage
  setAuth('new', 'newref', false); // sessionStorage; must drop the localStorage one
  expect(localStorage.getItem(A)).toBeNull();
  expect(sessionStorage.getItem(A)).toBe('new');
  expect(getAccessToken()).toBe('new');
});

test('refresh (no remember arg) keeps tokens in the active store', () => {
  setAuth('acc', 'ref', false); // session session
  setAuth('acc2', 'ref2'); // silent refresh
  expect(sessionStorage.getItem(A)).toBe('acc2');
  expect(localStorage.getItem(A)).toBeNull();
});

test('stored user follows the active store and reads back', () => {
  setAuth('acc', 'ref', true);
  const u = { user_id: 1, email: 'a@b.c', role: 'admin', is_active: true, pages: [], is_admin: true };
  setStoredUser(u);
  expect(localStorage.getItem('pv_auth_user')).not.toBeNull();
  expect(getStoredUser()?.email).toBe('a@b.c');
});

test('clearAuth wipes both stores', () => {
  setAuth('acc', 'ref', true);
  setAuth('acc', 'ref', false);
  // (only session now holds it, but force both populated)
  localStorage.setItem(A, 'x');
  clearAuth();
  expect(localStorage.getItem(A)).toBeNull();
  expect(sessionStorage.getItem(A)).toBeNull();
  expect(getAccessToken()).toBeNull();
});
