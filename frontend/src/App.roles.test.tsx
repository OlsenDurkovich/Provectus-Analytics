// Role-based UI gating: admins see Users + Flights nav; viewers don't, and
// viewers hitting an admin route get redirected to Overview.
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, beforeEach } from 'vitest';
import App from './App';
import { AuthProvider } from './auth/AuthContext';

function mockFetch(role: string) {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/auth/me')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({ user_id: 1, email: 'u@example.com', role, is_active: true }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: async () => ({
        mode: 'synthetic',
        liveClientCount: 0,
        dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 },
      }),
    });
  });
}

function seed(role: string) {
  localStorage.setItem('pv_auth_access', 'fake-access');
  localStorage.setItem('pv_auth_refresh', 'fake-refresh');
  localStorage.setItem(
    'pv_auth_user',
    JSON.stringify({ user_id: 1, email: 'u@example.com', role, is_active: true }),
  );
}

function renderAt(path: string, role: string) {
  seed(role);
  mockFetch(role);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <App />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
});

test('admin sees Users and Flights nav links', () => {
  renderAt('/', 'admin');
  // Target the nav links specifically — "Flights" also appears as a
  // data-state row label, so match by link role.
  expect(screen.queryByRole('link', { name: /users/i })).not.toBeNull();
  expect(screen.queryByRole('link', { name: /flights/i })).not.toBeNull();
});

test('viewer does not see Users or Flights nav links', () => {
  renderAt('/', 'viewer');
  expect(screen.queryByRole('link', { name: /users/i })).toBeNull();
  expect(screen.queryByRole('link', { name: /flights/i })).toBeNull();
});

test('viewer hitting /users is redirected to Overview', () => {
  renderAt('/users', 'viewer');
  // No Users management content; redirected to Overview instead.
  expect(screen.queryByText('Add user')).toBeNull();
  expect(screen.getAllByText('Overview').length).toBeGreaterThanOrEqual(1);
});

test('admin viewing /users sees the management screen', () => {
  renderAt('/users', 'admin');
  expect(screen.getByText('Add user')).toBeInTheDocument();
});
