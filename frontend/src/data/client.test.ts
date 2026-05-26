import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { client, ApiError } from './client';

describe('client', () => {
  const origFetch = globalThis.fetch;
  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });
  afterEach(() => {
    globalThis.fetch = origFetch;
  });

  test('getMeta hits /api/meta and returns parsed JSON', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        mode: 'synthetic',
        liveClientCount: 0,
        dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 },
      }),
    });
    const meta = await client.getMeta();
    expect(meta.mode).toBe('synthetic');
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/meta', expect.anything());
  });

  test('throws ApiError on non-2xx', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'boom',
    });
    await expect(client.getMeta()).rejects.toBeInstanceOf(ApiError);
  });

  test('getClients passes optional rating param', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    await client.getClients('12mo', 'PPL');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/students?range=12mo&rating=PPL',
      expect.anything(),
    );
  });

  test('getRatingCohort calls /api/ratings/PPL/cohort', async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [
        { studentId: '1', name: 'Alice', hours: 60.0, cost: 15000, days: 400 },
      ],
    });
    const result = await client.getRatingCohort('PPL');
    expect(result).toHaveLength(1);
    expect(result[0].studentId).toBe('1');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/ratings/PPL/cohort',
      expect.anything(),
    );
  });
});
