import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { test, expect, vi, beforeEach, afterEach } from 'vitest';
import { useRatingCohorts } from './queries';
import type { RatingCode } from './types';

const origFetch = globalThis.fetch;

beforeEach(() => {
  globalThis.fetch = vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/ratings/PPL/cohort')) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          { studentId: '1', name: 'Alice', hours: 60, cost: 15000, days: 380 },
        ],
      });
    }
    if (url.includes('/api/ratings/IFR/cohort')) {
      return Promise.resolve({
        ok: true,
        json: async () => [
          { studentId: '2', name: 'Bob', hours: 50, cost: 12000, days: 300 },
        ],
      });
    }
    return Promise.resolve({ ok: true, json: async () => [] });
  });
});

afterEach(() => {
  globalThis.fetch = origFetch;
});

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  );
}

test('useRatingCohorts fans out to one query per code', async () => {
  const codes: RatingCode[] = ['PPL', 'IFR'];
  const { result } = renderHook(() => useRatingCohorts(codes), { wrapper: wrapper() });

  await waitFor(() => {
    expect(result.current.get('PPL')?.data).toBeTruthy();
    expect(result.current.get('IFR')?.data).toBeTruthy();
  });
  expect(result.current.get('PPL')!.data!.length).toBe(1);
  expect(result.current.get('PPL')!.data![0].name).toBe('Alice');
  expect(result.current.get('IFR')!.data![0].name).toBe('Bob');
});

test('useRatingCohorts returns empty map for empty codes', () => {
  const { result } = renderHook(() => useRatingCohorts([]), { wrapper: wrapper() });
  expect(result.current.size).toBe(0);
});
