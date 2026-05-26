import { render, screen, fireEvent } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { ClientsTable } from './ClientsTable';
import type { ClientRow } from '../data/types';

const rows: ClientRow[] = [
  { id: '1', name: 'Alex Doe', rating: 'PPL', progressPct: 0.5, hoursToDate: 40, daysEnrolled: 60, status: 'Active' },
  { id: '2', name: 'Jamie Lee', rating: 'IFR', progressPct: 0.95, hoursToDate: 38, daysEnrolled: 180, status: 'On checkride' },
];

test('renders rows', () => {
  render(<ClientsTable rows={rows} />);
  expect(screen.getByText('Alex Doe')).toBeTruthy();
  expect(screen.getByText('Jamie Lee')).toBeTruthy();
});

test('renders the row count chip', () => {
  render(<ClientsTable rows={rows} />);
  expect(screen.getByText(/2 clients/)).toBeTruthy();
});

test('search filters by name', () => {
  render(<ClientsTable rows={rows} />);
  const search = screen.getByPlaceholderText(/Filter by name/);
  fireEvent.change(search, { target: { value: 'Alex' } });
  expect(screen.queryByText('Jamie Lee')).toBeNull();
  expect(screen.getByText('Alex Doe')).toBeTruthy();
});

test('filterRating prop hides non-matching rows + clear button calls onClearFilter', () => {
  const onClearFilter = vi.fn();
  render(<ClientsTable rows={rows} filterRating="PPL" onClearFilter={onClearFilter} />);
  expect(screen.queryByText('Jamie Lee')).toBeNull();
  fireEvent.click(screen.getByText('Clear filter'));
  expect(onClearFilter).toHaveBeenCalled();
});
