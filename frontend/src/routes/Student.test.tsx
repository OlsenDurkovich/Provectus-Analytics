import { render, waitFor, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Student from './Student';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/PPL/cohort')) {
      body = [
        { studentId: 'student-1', name: 'Alex Martinez', hours: 65, cost: 15000, days: 165 },
        { studentId: 'other-1', name: 'Other A', hours: 60, cost: 14500, days: 155 },
        { studentId: 'other-2', name: 'Other B', hours: 70, cost: 16000, days: 175 },
      ];
    } else if (url.includes('/api/students/')) {
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
        { id: 'student-1', name: 'Alex Martinez', rating: 'PPL', progressPct: 0.9, hoursToDate: 65, daysEnrolled: 160, status: 'Completed', costToDate: 14500, instructor: 'Doug Hayes', sparkline: [2, 3, 5, 6, 8, 7, 6, 5] },
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

test('renders 3 mini scatter strips per rating block', async () => {
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
});

test('injects student as in-progress dot when not in cohort', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/ratings/IFR/cohort')) {
      body = [
        { studentId: 'other-1', name: 'Other A', hours: 45, cost: 11000, days: 120 },
        { studentId: 'other-2', name: 'Other B', hours: 55, cost: 13000, days: 140 },
      ];
    } else if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
        perRating: [
          {
            rating: 'IFR',
            name: 'Instrument Rating',
            n: 8,
            hours: 32, // student has hours but no checkride
            cost: 9000,
            days: 90,
            medianHrs: 50,
            medianCost: 12000,
            medianDays: 130,
            lowSample: false,
          },
        ],
      };
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Instrument Rating')).toBeTruthy());
  await waitFor(() => {
    const warnDot = container.querySelector('.rating-block circle[fill="var(--warn)"]');
    expect(warnDot).toBeTruthy();
  });
});

test('renders without warn dot when student is in cohort', async () => {
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  await waitFor(() => {
    const svgs = container.querySelectorAll('.rating-block svg');
    expect(svgs.length).toBe(3);
  });
  const warnDot = container.querySelector('.rating-block circle[fill="var(--warn)"]');
  expect(warnDot).toBeNull();
});

test('renders fallback note when lowSample is true', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    let body: unknown = [];
    if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
        perRating: [
          {
            rating: 'MEI',
            name: 'Multi-Engine Instructor',
            n: 2,
            hours: 10,
            cost: 3000,
            days: 30,
            medianHrs: 12,
            medianCost: 3200,
            medianDays: 35,
            lowSample: true,
          },
        ],
      };
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() =>
    expect(screen.getByText('Multi-Engine Instructor')).toBeTruthy(),
  );
  expect(screen.getByText('Distribution hidden — low sample')).toBeTruthy();
  const stripSvgs = container.querySelectorAll('.rating-block-strips svg');
  expect(stripSvgs.length).toBe(0);
});

test('renders nothing in strip slot when cohort fetch errors', async () => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/cohort')) {
      return Promise.resolve({ ok: false, json: async () => ({}) });
    }
    let body: unknown = [];
    if (url.includes('/api/students/')) {
      body = {
        id: 'student-1',
        name: 'Alex Martinez',
        timeline: [],
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
    } else {
      body = [];
    }
    return Promise.resolve({ ok: true, json: async () => body });
  });
  const { container } = render(wrap('/students/student-1'));
  await waitFor(() => expect(screen.getByText('Private Pilot')).toBeTruthy());
  // Numeric MiniKpis still render
  expect(screen.getByText('Hours')).toBeTruthy();
  // Strips should be absent (error path hides strips)
  await waitFor(() => {
    const stripSvgs = container.querySelectorAll('.rating-block-strips svg');
    expect(stripSvgs.length).toBe(0);
  });
});
