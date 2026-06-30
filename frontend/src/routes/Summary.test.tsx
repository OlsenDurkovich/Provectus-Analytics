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
      const r = (url.match(/range=(\w+)/) || [])[1] || 'all';
      const rc = r === '6mo' ? '4' : r === '12mo' ? '12' : '81';
      const fh = r === '6mo' ? '239' : r === '12mo' ? '771' : '4,455';
      body = [
        { key: 'ratings_completed', label: 'Ratings completed', value: rc, sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
        { key: 'flight_hours', label: 'Flight hours', value: fh, sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
        { key: 'active_clients', label: 'Active students', value: '4', sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
        { key: 'total_billed', label: 'Total billed', value: '$1.2M', sub: '', delta: 0, positive: true, spark: [], color: '#fff' },
      ];
    } else if (url.match(/\/api\/ratings\?/)) {
      const m = url.match(/metric=(\w+)/);
      body = bars(m ? m[1] : 'hours');
    } else if (url.includes('/api/insights')) {
      body = {
        atRiskThresholdPct: 0.25,
        atRisk: [{ studentId: '1', name: 'Jamie Chen', rating: 'AMEL', hours: 18, medianHours: 14, pctOverHours: 0.29, cost: 9300, medianCost: 7080, pctOverCost: 0.31, days: 70, worstPct: 0.31, status: 'Completed' }],
        strengths: [{ rating: 'COM', medianHours: 28, medianCost: 27600, instructors: [
          { instructor: 'Sarah Phillips', rating: 'COM', n: 5, avgHours: 24.1, avgCost: 24000, vsRestHoursPct: -0.18, vsRestCostPct: -0.18, comparable: true, lowSample: false, rank: 1 },
          { instructor: 'Jenny Park', rating: 'COM', n: 4, avgHours: 30.5, avgCost: 31000, vsRestHoursPct: 0.14, vsRestCostPct: 0.14, comparable: true, lowSample: false, rank: 2 },
        ] }],
        efficiency: [{ instructor: 'Sarah Phillips', students: 30, ratings: 7, avgHoursVsRestPct: -0.04, avgCostVsRestPct: -0.04, score: -0.04, rank: 1, lowSample: false }],
        predictions: [
          { studentId: '21', name: 'Henry Walsh', rating: 'PPL', currentHours: 59.5, medianHours: 64, pacePerWeek: 0.6, weeksRemaining: 7.3, projectedDate: '2026-08-20', lastFlight: '2026-05-11', daysSinceLastFlight: 50, status: 'on_track' },
          { studentId: '22', name: 'Grace Liu', rating: 'PPL', currentHours: 34.8, medianHours: 64, pacePerWeek: 0.3, weeksRemaining: 97.9, projectedDate: '2028-05-15', lastFlight: '2026-04-23', daysSinceLastFlight: 68, status: 'behind_pace' },
          { studentId: '10', name: 'Tyler Brooks', rating: 'PPL', currentHours: 26, medianHours: 64, pacePerWeek: 0, weeksRemaining: null, projectedDate: null, lastFlight: '2024-01-26', daysSinceLastFlight: 886, status: 'stalled' },
        ],
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

test('renders the overview half (KPIs, per-rating table, highlights)', async () => {
  render(wrap(<Summary />));
  await waitFor(() => expect(screen.getByText('Ratings completed')).toBeTruthy());
  expect(screen.getByText('81')).toBeTruthy();                 // all-time KPI value
  expect(screen.getByText('Private Pilot')).toBeTruthy();      // per-rating table
  expect(screen.getByText('$16,500')).toBeTruthy();
  expect(screen.getByText('Sarah Phillips')).toBeTruthy();     // highlight
  expect(screen.getByText(/72 vs 363 days/)).toBeTruthy();
  expect(screen.getByRole('button', { name: /Print/ })).toBeTruthy();
  expect(screen.getByText(/Sample data/)).toBeTruthy();
  // billing is intentionally hidden from the owner view
  expect(screen.queryByText('Total billed')).toBeNull();
  // 12/6-month breakdown rendered (flight-hours 12mo=771, 6mo=239 are unique)
  const breakdown = screen.getByText(
    (_t, el) => el?.className === 'summary-kpi-breakdown' && (el.textContent || '').includes('771'),
  );
  expect((breakdown.textContent || '').includes('239')).toBe(true);
});

test('renders the "right now" half (pipeline, attention lists, upcoming, instructors)', async () => {
  render(wrap(<Summary />));
  await waitFor(() => expect(screen.getByText(/Right now/)).toBeTruthy());
  expect(screen.getByText('Behind pace')).toBeTruthy();
  expect(screen.getByText('Stalled')).toBeTruthy();
  expect(screen.getByText('Needs attention')).toBeTruthy();
  expect(screen.getByText('Grace Liu')).toBeTruthy();
  expect(screen.getByText('Jamie Chen')).toBeTruthy();         // at-risk student
  expect(screen.getByText(/Upcoming checkrides/)).toBeTruthy();
  expect(screen.getByText('Henry Walsh')).toBeTruthy();
  // instructors-to-develop surfaces the one deviating >10% over peers
  expect(screen.getByText('Instructors to develop')).toBeTruthy();
  expect(screen.getByText('Jenny Park')).toBeTruthy();
  expect(screen.getByText(/may need COM development/)).toBeTruthy();
});
