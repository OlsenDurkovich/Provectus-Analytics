import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Overview from './Overview';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/kpis')) {
      body = [
        { key: 'ratings_completed', label: 'Ratings completed', value: '12', sub: 'last 12 months', delta: 0, positive: true, spark: [1, 2, 3], color: '#6E56F8' },
        { key: 'active_clients', label: 'Active clients', value: '27', sub: 'last 12 months', delta: 0, positive: true, spark: [1, 2, 3], color: '#3DD68C' },
        { key: 'flight_hours', label: 'Flight hours', value: '1,697', sub: 'last 12 months', delta: 0, positive: true, spark: [1, 2, 3], color: '#22D3EE' },
        { key: 'total_billed', label: 'Total billed', value: '$501k', sub: 'last 12 months', delta: 0, positive: true, spark: [1, 2, 3], color: '#F59E0B' },
      ];
    } else if (url.includes('/api/heatmap')) {
      body = { rows: Array.from({ length: 7 }, () => Array(12).fill(0)), buckets: Array(12).fill('x') };
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders the Overview page head', () => {
  render(wrap(<Overview range="12mo" />));
  expect(screen.getByText('All ratings')).toBeTruthy();
  expect(screen.getByText(/Cohort overview/)).toBeTruthy();
});

test('renders KPI cards after data loads', async () => {
  render(wrap(<Overview range="12mo" />));
  // Wait on a KPI-only label — "Ratings completed" appears in both a KPI card and a chart card title.
  await waitFor(() => expect(screen.getByText('Active clients')).toBeTruthy());
  expect(screen.getByText('Flight hours')).toBeTruthy();
  expect(screen.getByText('Total billed')).toBeTruthy();
  expect(screen.getByText('27')).toBeTruthy();  // active clients KPI value
});
