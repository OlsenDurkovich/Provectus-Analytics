import { render, waitFor, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, afterEach, beforeEach } from 'vitest';
import Flights from './Flights';

let fetchSpy: ReturnType<typeof vi.fn>;
const origFetch = globalThis.fetch;

const SAMPLE_FLIGHT = {
  id: '42',
  date: '2025-09-12',
  client: 'Alex Martinez',
  instructor: 'Doug Hayes',
  type: 'Dual flight training',
  billing: 'Hobbs',
  acClass: 'SE_BASIC',
  ground: 'Flight (0)',
  hours: 1.4,
  cost: 410,
};

beforeEach(() => {
  fetchSpy = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
    if (url.startsWith('/api/instructors')) {
      return Promise.resolve({
        ok: true,
        json: async () => [{ id: 'Doug Hayes', name: 'Doug Hayes', hours: 100, students: 4, passRate: 0.9 }],
      });
    }
    if (url.startsWith('/api/flights/') && opts?.method === 'PATCH') {
      return Promise.resolve({
        ok: true,
        json: async () => ({ ...SAMPLE_FLIGHT, ground: 'Ground (1)' }),
      });
    }
    if (url.startsWith('/api/flights')) {
      return Promise.resolve({ ok: true, json: async () => [SAMPLE_FLIGHT] });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
  globalThis.fetch = fetchSpy as unknown as typeof fetch;
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrap() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <Flights />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('renders Flights page head', () => {
  render(wrap());
  expect(screen.getByText('Raw flight rows')).toBeTruthy();
  expect(screen.getByRole('heading', { level: 1, name: 'Flights' })).toBeTruthy();
});

test('renders flight row from API', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Alex Martinez')).toBeTruthy());
});

test('PATCH fires when changing ground cell', async () => {
  render(wrap());
  await waitFor(() => expect(screen.getByText('Flight (0)')).toBeTruthy());
  fireEvent.click(screen.getByText('Flight (0)'));
  fireEvent.click(screen.getByText('Ground (1)'));
  await waitFor(() => {
    const calls = fetchSpy.mock.calls.filter(([, opts]) => (opts as RequestInit | undefined)?.method === 'PATCH');
    expect(calls.length).toBeGreaterThan(0);
    const [url, opts] = calls[0];
    expect(url).toBe('/api/flights/42');
    const body = JSON.parse((opts as RequestInit).body as string);
    expect(body).toEqual({ field: 'is_ground_lesson', value: true });
  });
});
