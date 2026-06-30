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
        { instructor: 'Sarah Phillips', rating: 'COM', n: 5, avgHours: 24.1, avgCost: 24000, vsMedianHoursPct: -0.13, vsMedianCostPct: -0.13, lowSample: false, rank: 1 },
        { instructor: 'Jenny Park', rating: 'COM', n: 4, avgHours: 30.5, avgCost: 31000, vsMedianHoursPct: 0.10, vsMedianCostPct: 0.12, lowSample: false, rank: 2 },
      ],
    }],
    efficiency: [
      { instructor: 'Tom Reyes', students: 7, ratings: 4, avgHoursVsMedianPct: -0.03, avgCostVsMedianPct: -0.03, score: -0.03, rank: 1, lowSample: false },
      { instructor: 'Mike Anderson', students: 9, ratings: 7, avgHoursVsMedianPct: 0.06, avgCostVsMedianPct: 0.07, score: 0.06, rank: 2, lowSample: false },
    ],
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
});

test('threshold toggle refetches and can empty the at-risk list', async () => {
  render(wrap(<Insights />));
  await waitFor(() => expect(screen.getByText('Jamie Chen')).toBeTruthy());
  fireEvent.click(screen.getByRole('button', { name: '≥50%' }));
  await waitFor(() => expect(screen.getByText(/No one over 50%/)).toBeTruthy());
  expect(screen.queryByText('Jamie Chen')).toBeNull();
});
