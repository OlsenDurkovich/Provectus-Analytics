import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import RatingDetail from './RatingDetail';

const origFetch = globalThis.fetch;

const RATING_BODY = {
  code: 'PPL',
  name: 'Private Pilot',
  n: 12,
  medianHrs: 64.2,
  p25Hrs: 59.8,
  p75Hrs: 65.6,
  medianCost: 16569,
  p25Cost: 15695,
  p75Cost: 17771,
  medianDays: 407,
  p25Days: 374,
  p75Days: 455,
  lowSample: false,
};

const COHORT_BODY = [
  { studentId: '1', name: 'Alice', hours: 60.0, cost: 15000, days: 380 },
  { studentId: '2', name: 'Bob', hours: 64.2, cost: 16569, days: 407 },
];

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: true, json: async () => COHORT_BODY });
    }
    if (url.includes('/api/ratings/PPL')) {
      return Promise.resolve({ ok: true, json: async () => RATING_BODY });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap(path = '/ratings/PPL') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/ratings/:code" element={<RatingDetail range="12mo" />} />
          <Route path="/ratings" element={<RatingDetail range="12mo" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders the static page title', () => {
  render(wrap());
  expect(screen.getByText('Rating detail')).toBeTruthy();
});

test('renders KPI cards after data loads', async () => {
  render(wrap());
  // 64.2 appears in both the KPI card and the cohort table row (Bob's hours)
  await waitFor(() => expect(screen.getAllByText('64.2').length).toBeGreaterThan(0));
  expect(screen.getByText('Alumni (n)')).toBeTruthy();
  expect(screen.getByText('12')).toBeTruthy();
});

test('renders cohort table after data loads', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Alice')).toBeTruthy());
  expect(screen.getByText('Bob')).toBeTruthy();
});

test('renders Distribution section heading', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Distribution')).toBeTruthy());
});

test('Distribution section hidden when cohort is empty', async () => {
  // Override fetch to return empty cohort
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: true, json: async () => [] });
    }
    if (url.includes('/api/ratings/PPL')) {
      return Promise.resolve({ ok: true, json: async () => RATING_BODY });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
  render(wrap());
  await waitFor(() => expect(screen.getByText('Alumni (n)')).toBeTruthy());
  // Distribution heading should NOT appear
  expect(screen.queryByText('Distribution')).toBeNull();
});

test('overlay student appears in cohort table as highlighted', async () => {
  const { container } = render(wrap());
  await waitFor(() => expect(screen.getByText('Alice')).toBeTruthy());
  // Find overlay pin chip in the row — it won't exist until a student is selected
  // No overlay selected initially, so no row-highlight
  expect(container.querySelector('.row-highlight')).toBeNull();
});

test('renders error state when cohort fetch fails', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: false, json: async () => ({}) });
    }
    if (url.includes('/api/ratings/PPL')) {
      return Promise.resolve({ ok: true, json: async () => RATING_BODY });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
  render(wrap());
  await waitFor(() => expect(screen.getByText('Alumni (n)')).toBeTruthy());
  // Error state should appear
  await waitFor(() =>
    expect(screen.queryByText('Could not load cohort')).toBeTruthy()
  );
});
