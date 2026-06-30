import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Insights from './Insights';

const origFetch = globalThis.fetch;

function payload(threshold: number) {
  return {
    atRiskThresholdPct: threshold,
    // Only surface the at-risk row when the threshold is loose (<=0.25).
    atRisk:
      threshold <= 0.25
        ? [{
            studentId: '1', name: 'Jamie Chen', rating: 'AMEL',
            hours: 18, medianHours: 14, pctOverHours: 0.29,
            cost: 9300, medianCost: 7080, pctOverCost: 0.31,
            days: 70, worstPct: 0.31, status: 'Completed',
          }]
        : [],
    strengths: [{
      rating: 'COM', medianHours: 28, medianCost: 27600,
      instructors: [
        { instructor: 'Sarah Phillips', rating: 'COM', n: 5, avgHours: 24.1, avgCost: 24000, vsRestHoursPct: -0.18, vsRestCostPct: -0.18, comparable: true, lowSample: false, rank: 1 },
        { instructor: 'Jenny Park', rating: 'COM', n: 4, avgHours: 30.5, avgCost: 31000, vsRestHoursPct: 0.14, vsRestCostPct: 0.15, comparable: true, lowSample: false, rank: 2 },
      ],
    }],
    efficiency: [
      { instructor: 'Tom Reyes', students: 7, ratings: 4, avgHoursVsRestPct: -0.031, avgCostVsRestPct: -0.039, score: -0.035, rank: 1, lowSample: false },
      { instructor: 'Mike Anderson', students: 9, ratings: 7, avgHoursVsRestPct: 0.066, avgCostVsRestPct: 0.06, score: 0.063, rank: 2, lowSample: false },
    ],
    predictions: [
      { studentId: '21', name: 'Henry Walsh', rating: 'PPL', currentHours: 59.5, medianHours: 64, pacePerWeek: 0.6, weeksRemaining: 7.3, projectedDate: '2026-08-20', lastFlight: '2026-05-11', daysSinceLastFlight: 50, status: 'on_track' },
      { studentId: '10', name: 'Tyler Brooks', rating: 'PPL', currentHours: 26, medianHours: 64, pacePerWeek: 0, weeksRemaining: null, projectedDate: null, lastFlight: '2024-01-26', daysSinceLastFlight: 886, status: 'stalled' },
    ],
    cadence: {
      rating: 'PPL', n: 24, buckets: [
        { label: 'Under 1.5×/week', n: 16, avgCadence: 0.7, avgHours: 64.2, avgCost: 17029, avgDays: 363 },
        { label: '2.5×+/week', n: 4, avgCadence: 3.0, avgHours: 55.6, avgCost: 14654, avgDays: 72 },
      ],
    },
  };
}

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    const m = url.match(/threshold=([0-9.]+)/);
    const threshold = m ? Number(m[1]) : 0.25;
    return Promise.resolve({ ok: true, json: async () => payload(threshold) });
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

test('renders the three insight sections with data', async () => {
  render(wrap(<Insights />));
  await waitFor(() => expect(screen.getByText('At-risk students')).toBeTruthy());
  expect(screen.getByText('Instructor strengths · by rating')).toBeTruthy();
  expect(screen.getByText('Instructor efficiency ranking')).toBeTruthy();
  // at-risk row + best instructor are present
  expect(screen.getByText('Jamie Chen')).toBeTruthy();
  expect(screen.getByText('Sarah Phillips')).toBeTruthy();
  expect(screen.getByText('Tom Reyes')).toBeTruthy();
  // #4 prediction + #5 cadence sections render
  expect(screen.getByText(/Completion forecast/)).toBeTruthy();
  expect(screen.getByText('Henry Walsh')).toBeTruthy();
  expect(screen.getByText(/On track/)).toBeTruthy();
  expect(screen.getByText(/Stalled/)).toBeTruthy();
  expect(screen.getByText(/Training cadence vs outcomes/)).toBeTruthy();
});

test('threshold toggle refetches and can empty the at-risk list', async () => {
  render(wrap(<Insights />));
  await waitFor(() => expect(screen.getByText('Jamie Chen')).toBeTruthy());
  fireEvent.click(screen.getByRole('button', { name: '≥50%' }));
  await waitFor(() => expect(screen.getByText(/No one over 50%/)).toBeTruthy());
  expect(screen.queryByText('Jamie Chen')).toBeNull();
});
