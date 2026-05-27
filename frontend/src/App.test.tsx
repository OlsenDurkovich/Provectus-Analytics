import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi, beforeEach } from 'vitest';
import App from './App';
import { AuthProvider } from './auth/AuthContext';

function mockMetaFetch() {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (typeof url === 'string' && url.includes('/api/auth/me')) {
      return Promise.resolve({
        ok: true,
        json: async () => ({
          user_id: 1, email: 'test@example.com',
          role: 'admin', is_active: true,
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

function renderAt(path: string) {
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
  // Pre-seed localStorage so AuthProvider hydrates an authenticated session.
  localStorage.setItem('pv_auth_access', 'fake-access');
  localStorage.setItem('pv_auth_refresh', 'fake-refresh');
  localStorage.setItem(
    'pv_auth_user',
    JSON.stringify({
      user_id: 1, email: 'test@example.com',
      role: 'admin', is_active: true,
    }),
  );
});

test('renders sidebar nav with all five tabs', () => {
  mockMetaFetch();
  renderAt('/');
  expect(screen.getByText('Rating detail')).toBeInTheDocument();
  expect(screen.getByText('Instructor')).toBeInTheDocument();
  // "Overview", "Student", "Flights" appear in both nav and breadcrumb / page-head;
  // use getAllByText for those
  expect(screen.getAllByText('Overview').length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText('Student').length).toBeGreaterThanOrEqual(1);
  expect(screen.getAllByText('Flights').length).toBeGreaterThanOrEqual(1);
});

test('changes breadcrumb when route changes', () => {
  mockMetaFetch();
  renderAt('/flights');
  // The breadcrumb-current span shows the route name
  const flightsCells = screen.getAllByText('Flights');
  expect(flightsCells.length).toBeGreaterThanOrEqual(2);
});

test('synthetic data badge appears in topbar', () => {
  mockMetaFetch();
  renderAt('/');
  expect(screen.getByText('Synthetic data')).toBeInTheDocument();
});
