import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import PublicTransparency from './PublicTransparency';

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <PublicTransparency />
    </QueryClientProvider>,
  );
}

test('renders a rating with its median cost + sample-data notice (synthetic)', async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      data_mode: 'synthetic',
      ratings: [{
        code: 'PPL', label: 'Private Pilot', n: 14, low_sample: false,
        median_cost: 18500, p25_cost: 16000, p75_cost: 21000,
        median_hours: 62.5, p25_hours: 55, p75_hours: 71, median_days: 240,
      }],
    }),
  });
  renderPage();
  expect(await screen.findByText('Private Pilot')).toBeInTheDocument();
  expect(screen.getByText('$18,500')).toBeInTheDocument();
  expect(screen.getByText(/Sample data/)).toBeInTheDocument();
});

test('shows low-sample badge and no sample notice when data is real', async () => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      data_mode: 'real',
      ratings: [{
        code: 'MEI', label: 'Multi-Engine Instructor', n: 3, low_sample: true,
        median_cost: 9000, p25_cost: 8000, p75_cost: 10000,
        median_hours: 15, p25_hours: 12, p75_hours: 18, median_days: 60,
      }],
    }),
  });
  renderPage();
  expect(await screen.findByText('low sample')).toBeInTheDocument();
  expect(screen.queryByText(/Sample data/)).toBeNull();
});
