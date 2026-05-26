import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Instructor from './Instructor';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.match(/\/api\/instructors\/[^?]+/)) {
      body = {
        id: 'Doug Hayes',
        name: 'Doug Hayes',
        students: [
          { id: 's1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.95, hoursToDate: 62, daysEnrolled: 160, status: 'Completed', costToDate: 14500, instructor: 'Doug Hayes', sparkline: [4, 6, 8, 7, 5, 4, 3, 2] },
        ],
        perRating: [
          { rating: 'PPL', n: 5, medianHrs: 61, medianCost: 14500, medianDays: 158 },
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
