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
        json: async () => ({
          user_id: 1, email: 'u@example.com', role, is_active: true,
          pages: ['overview', 'ratings', 'students', 'instructors'],
          is_admin: role === 'admin',
        }),
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
    JSON.stringify({
      user_id: 1, email: 'u@example.com', role, is_active: true,
      pages: ['overview', 'ratings', 'students', 'instructors'],
      is_admin: role === 'admin',
    }),
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

// --- per-user page access --------------------------------------------------

function renderCustom(path: string, user: Record<string, unknown>, fetchImpl: (url: string) => Promise<unknown>) {
  localStorage.setItem('pv_auth_access', 'fake-access');
  localStorage.setItem('pv_auth_refresh', 'fake-refresh');
  localStorage.setItem('pv_auth_user', JSON.stringify(user));
  globalThis.fetch = vi.fn().mockImplementation(fetchImpl);
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

const META = {
  mode: 'synthetic', liveClientCount: 0,
  dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 },
};

test('viewer with only Overview sees just that nav link', () => {
  const u = { user_id: 1, email: 'v@example.com', role: 'viewer', is_active: true, pages: ['overview'], is_admin: false };
  renderCustom('/', u, (url) =>
    Promise.resolve({ ok: true, json: async () => (url.includes('/api/auth/me') ? u : META) }),
  );
  expect(screen.queryByRole('link', { name: /overview/i })).not.toBeNull();
  expect(screen.queryByRole('link', { name: /rating detail/i })).toBeNull();
  expect(screen.queryByRole('link', { name: /^student/i })).toBeNull();
  expect(screen.queryByRole('link', { name: /^instructor/i })).toBeNull();
});

// --- student role ----------------------------------------------------------

const STUDENT = {
  user_id: 3, email: 'kid@example.com', role: 'student', is_active: true,
  pages: [], is_admin: false, student_id: 5,
};
const TRAINING = { id: '5', name: 'Pat Lee', timeline: [], perRating: [] };

function studentFetch(url: string) {
  if (url.includes('/api/auth/me')) return Promise.resolve({ ok: true, json: async () => STUDENT });
  if (url.includes('/api/me/training')) return Promise.resolve({ ok: true, json: async () => TRAINING });
  return Promise.resolve({ ok: true, json: async () => META });
}

test('student landing on / is routed to My training and sees only that nav', async () => {
  renderCustom('/', STUDENT, studentFetch);
  expect(await screen.findByRole('link', { name: /my training/i })).not.toBeNull();
  // No internal dashboard or admin nav.
  expect(screen.queryByRole('link', { name: /overview/i })).toBeNull();
  expect(screen.queryByRole('link', { name: /^rating detail/i })).toBeNull();
  expect(screen.queryByRole('link', { name: /users/i })).toBeNull();
});

test('student hitting an admin route is redirected to My training', async () => {
  renderCustom('/users', STUDENT, studentFetch);
  expect(screen.queryByText('Add user')).toBeNull();
  expect(await screen.findByRole('heading', { name: /my training/i })).toBeInTheDocument();
});

test('admin Users screen shows per-user page checkboxes', async () => {
  const admin = { user_id: 1, email: 'a@example.com', role: 'admin', is_active: true, pages: ['overview', 'ratings', 'students', 'instructors'], is_admin: true };
  const viewer = { user_id: 2, email: 'v@example.com', role: 'viewer', is_active: true, pages: ['overview'], is_admin: false };
  renderCustom('/users', admin, (url) => {
    if (url.includes('/api/auth/me')) return Promise.resolve({ ok: true, json: async () => admin });
    if (url.includes('/api/users')) return Promise.resolve({ ok: true, json: async () => [admin, viewer] });
    return Promise.resolve({ ok: true, json: async () => META });
  });
  expect(await screen.findByText('v@example.com')).toBeInTheDocument();
  // the page-access controls render
  expect(screen.getAllByText('Pages this user can see').length).toBeGreaterThanOrEqual(1);
  // a Reset password control per user
  expect(screen.getAllByText('Reset password').length).toBeGreaterThanOrEqual(1);
});
