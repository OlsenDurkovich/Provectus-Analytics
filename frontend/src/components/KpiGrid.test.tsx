import { render, screen, fireEvent } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { KpiGrid } from './KpiGrid';

const sample = [
  { key: 'a', label: 'A', value: '1', sub: 'sub', delta: 0, positive: true, comparable: true, spark: [1, 2, 3], color: '#fff' },
  { key: 'b', label: 'B', value: '2', sub: 'sub', delta: 0, positive: true, comparable: true, spark: [1, 2, 3], color: '#fff' },
];

test('renders KPI cards', () => {
  render(<KpiGrid kpis={sample} focusedKey={null} onFocus={() => {}} />);
  expect(screen.getByText('A')).toBeTruthy();
  expect(screen.getByText('B')).toBeTruthy();
});

test('clicking a card calls onFocus with its key', () => {
  const onFocus = vi.fn();
  render(<KpiGrid kpis={sample} focusedKey={null} onFocus={onFocus} />);
  fireEvent.click(screen.getByText('A').closest('button')!);
  expect(onFocus).toHaveBeenCalledWith('a');
});

test('clicking the already-focused card un-focuses it', () => {
  const onFocus = vi.fn();
  render(<KpiGrid kpis={sample} focusedKey="a" onFocus={onFocus} />);
  fireEvent.click(screen.getByText('A').closest('button')!);
  expect(onFocus).toHaveBeenCalledWith(null);
});
