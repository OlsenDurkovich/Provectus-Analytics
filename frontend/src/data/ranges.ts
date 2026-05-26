import type { RangeKey } from './types';

export const RANGES: Record<RangeKey, { label: string; cmp: string }> = {
  '30d': { label: 'Last 30 days', cmp: 'previous 30 days' },
  '90d': { label: 'Last 90 days', cmp: 'previous 90 days' },
  '6mo': { label: 'Last 6 months', cmp: 'previous 6 months' },
  '12mo': { label: 'Last 12 months', cmp: 'previous 12 months' },
  ytd: { label: 'Year to date', cmp: 'same period last year' },
  all: { label: 'All time', cmp: '—' },
};

export const RANGE_KEYS: RangeKey[] = ['30d', '90d', '6mo', '12mo', 'ytd', 'all'];
