import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Instructor from './Instructor';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/PPL/cohort')) {
      body = [
        { studentId: 's1', name: 'Alex Martinez', hours: 62, cost: 14500, days: 158 },
        { studentId: 's2', name: 'Other A', hours: 65, cost: 15500, days: 170 },
        { studentId: 's3', name: 'Other B', hours: 70, cost: 16500, days: 180 },
      ];
    } else if (url.match(/\/api\/instructors\/[^?]+/)) {
      body = {
        id: 'Doug Hayes',
        name: 'Doug Hayes',
        students: [
          { id: 's1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.95, hoursToDate: 62, daysEnrolled: 160, status: 'Completed', costToDate: 14500, instructor: 'Doug Hayes', sparkline: [4, 6, 8, 7, 5, 4, 3, 2] },
        ],
        perRating: [
          { rating: 'PPL', n: 1, avgHrs: 62, avgCost: 14500, avgDays: 158, studentIds: ['s1'] },
        ],
      };
    } else if (url.includes('/api/instructors')) {
      body = [
        { id: 'Doug Hayes', name: 'Doug Hayes', hours: 412, students: 6, passRate: 0.9 },
      ];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap(initialPath = '/instructors') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/instructors/:id?" element={<Instructor />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders Instructor page head', () => {
  render(wrap());
  expect(screen.getByText('People')).toBeTruthy();
  expect(screen.getByRole('heading', { level: 1, name: 'Instructor' })).toBeTruthy();
});

test('shows instructor detail after selecting one', async () => {
  render(wrap('/instructors/Doug%20Hayes'));
  await waitFor(() => expect(screen.getByText('Alex Martinez')).toBeTruthy());
  expect(screen.getByText('Ratings taught')).toBeTruthy();
  expect(screen.getByText('Student roster')).toBeTruthy();
});

test('renders per-rating block with 3 scatter strips and correct highlight', async () => {
  const { container } = render(wrap('/instructors/Doug%20Hayes'));
  await waitFor(() => expect(screen.getByText('Per rating vs cohort')).toBeTruthy());
  // The PPL rating chip should appear in the block head
  const ppl = Array.from(container.querySelectorAll('.rating-chip')).find(
    (el) => el.textContent === 'PPL',
  );
  expect(ppl).toBeTruthy();
  // 3 SVGs (mini scatter strips) inside the rating block
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
  // Exactly 1 student is highlighted (s1 — Alex Martinez)
  const accentCircles = Array.from(
    container.querySelectorAll('.rating-block circle[fill="var(--accent)"]'),
  );
  // 3 strips × 1 highlighted student per strip = 3 accent circles
  expect(accentCircles.length).toBe(3);
});
