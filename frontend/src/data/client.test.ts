import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { client, ApiError } from './client';

describe('client', () => {
  const origFetch = global.fetch;
  beforeEach(() => {
    global.fetch = vi.fn();
  });
  afterEach(() => {
    global.fetch = origFetch;
  });

  test('getMeta hits /api/meta and returns parsed JSON', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => ({
        mode: 'synthetic',
        liveClientCount: 0,
        dataState: { flights: 0, invoices: 0, students: 0, surveys: 0, overrides: 0 },
      }),
    });
    const meta = await client.getMeta();
    expect(meta.mode).toBe('synthetic');
    expect(global.fetch).toHaveBeenCalledWith('/api/meta', expect.anything());
  });

  test('throws ApiError on non-2xx', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      text: async () => 'boom',
    });
    await expect(client.getMeta()).rejects.toBeInstanceOf(ApiError);
  });

  test('getClients passes optional rating param', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    await client.getClients('12mo', 'PPL');
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/students?range=12mo&rating=PPL',
      expect.anything(),
    );
  });
});
