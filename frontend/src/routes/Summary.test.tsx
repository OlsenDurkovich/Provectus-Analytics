import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Summary from './Summary';

const origFetch = globalThis.fetch;

const bars = (metric: string) => [
  { code: 'PPL', name: 'Private Pilot', n: 24, median: metric === 'cost' ? 16500 : metric === 'days' ? 200 : 64, p25: 0, p75: 0 },
  { code: 'AMEL', name: 'Multi-Engine', n: 11, median: metric === 'cost' ? 7000 : metric === 'days' ? 69 : 15, p25: 0, p75: 0 },
];

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = {};
    if (url.includes('/api/kpis')) {
      body = [
        { key: 'ratings_completed', label: 'Ratings completed', value: '81', sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
        { key: 'active_clients', label: 'Active students', value: '4', sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
      ];
    } else if (url.match(/\/api\/ratings\?/)) {
      const m = url.match(/metric=(\w+)/);
      body = bars(m ? m[1] : 'hours');
    } else if (url.includes('/api/insights')) {
      body = {
        atRiskThresholdPct: 0.25,
        atRisk: [{ studentId: '1', name: 'Jamie Chen', rating: 'AMEL', hours: 18, medianHours: 14, pctOverHours: 0.29, cost: 9300, medianCost: 7080, pctOverCost: 0.31, days: 70, worstPct: 0.31, status: 'Completed' }],
        strengths: [],
        efficiency: [{ instructor: 'Sarah Phillips', students: 30, ratings: 7, avgHoursVsRestPct: -0.04, avgCostVsRestPct: -0.04, score: -0.04, rank: 1, lowSample: false }],
        predictions: [{ studentId: '21', name: 'Henry Walsh', rating: 'PPL', currentHours: 59.5, medianHours: 64, pacePerWeek: 0.6, weeksRemaining: 7.3, projectedDate: '2026-08-20', lastFlight: '2026-05-11', daysSinceLastFlight: 50, status: 'on_track' }],
        cadence: { scope: 'all ratings', n: 104, buckets: [
          { label: '2.5×/week or less', n: 88, avgCadence: 0.9, avgDays: 363, costVsMedianPct: 0.01, hoursVsMedianPct: 0.01 },
          { label: 'Over 4×/week', n: 7, avgCadence: 4.8, avgDays: 72, costVsMedianPct: -0.09, hoursVsMedianPct: -0.09 },
        ] },
      };
    } else if (url.includes('/api/meta')) {
      body = { mode: 'synthetic', liveClientCount: 4, dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 } };
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});

afterEach(() => { globalThis.fetch = origFetch; });

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>;
}

test('renders KPIs, per-rating table, and highlights', async () => {
  render(wrap(<Summary />));
  await waitFor(() => expect(screen.getByText('Ratings completed')).toBeTruthy());
  // KPI value
  expect(screen.getByText('81')).toBeTruthy();
  // per-rating table: PPL row with merged metrics
  expect(screen.getByText('Private Pilot')).toBeTruthy();
  expect(screen.getByText('$16,500')).toBeTruthy();
  // highlights: best instructor + cadence finding + in-progress/at-risk
  expect(screen.getByText('Sarah Phillips')).toBeTruthy();
  expect(screen.getByText(/72 vs 363 days/)).toBeTruthy();
  expect(screen.getByText(/1 in progress · 1 at-risk/)).toBeTruthy();
  // print affordance + synthetic banner
  expect(screen.getByRole('button', { name: /Print/ })).toBeTruthy();
  expect(screen.getByText(/Sample data/)).toBeTruthy();
});
