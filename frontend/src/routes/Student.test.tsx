import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Student from './Student';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [
          {
            rating: 'PPL',
            start: '2024-01-01',
            end: '2024-06-15',
            milestones: [
              { name: 'first_solo', date: '2024-03-01' },
              { name: 'checkride', date: '2024-06-15' },
            ],
          },
        ],
        perRating: [
          {
            rating: 'PPL',
            name: 'Private Pilot',
            n: 12,
            hours: 65,
            cost: 15000,
            days: 165,
            medianHrs: 60,
            medianCost: 14000,
            medianDays: 150,
            lowSample: false,
          },
        ],
      };
    } else if (url.includes('/api/students')) {
      body = [
        { id: 'student-1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.9, hoursToDate: 65, daysEnrolled: 160, status: 'Completed' },
      ];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap(initialPath = '/students') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/students/:id?" element={<Student />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders Student page head', () => {
  render(wrap());
  expect(screen.getByText('Drill-down')).toBeTruthy();
  expect(screen.getByRole('heading', { level: 1, name: 'Student' })).toBeTruthy();
});

test('shows student detail after selecting one', async () => {
  render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Total flight hours')).toBeTruthy());
  expect(screen.getByText('Private Pilot')).toBeTruthy();
});
