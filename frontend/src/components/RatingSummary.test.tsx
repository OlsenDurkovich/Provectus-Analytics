import { render, screen, fireEvent, within } from '@testing-library/react';
import { expect, test } from 'vitest';
import { RatingSummary } from './RatingSummary';
import type { ClientRow } from '../data/types';

function row(p: Partial<ClientRow> & { id: string }): ClientRow {
  return {
    name: p.name ?? 'X',
    rating: p.rating ?? 'PPL',
    progressPct: 1,
    hoursToDate: p.hoursToDate ?? 50,
    daysEnrolled: p.daysEnrolled ?? 100,
    status: p.status ?? 'Completed',
    costToDate: p.costToDate ?? 10000,
    instructor: '',
    sparkline: [],
    ...p,
  };
}

const ROWS: ClientRow[] = [
  row({ id: '1', name: 'Ace', rating: 'PPL', costToDate: 8000, hoursToDate: 40 }),
  row({ id: '2', name: 'Mid', rating: 'PPL', costToDate: 10000, hoursToDate: 50 }),
  row({ id: '3', name: 'Slow', rating: 'PPL', costToDate: 12000, hoursToDate: 60 }),
  // in-progress should be ignored entirely
  row({ id: '4', name: 'Newbie', rating: 'PPL', costToDate: 500, status: 'Active' }),
];

test('average mode shows the mean of completed students only', () => {
  render(<RatingSummary rows={ROWS} />);
  // (8000+10000+12000)/3 = 10000 ; Newbie's 500 excluded
  expect(screen.getByText('$10,000')).toBeInTheDocument();
  expect(screen.getByText(/Average · n=3/)).toBeInTheDocument();
  expect(screen.queryByText('Newbie')).not.toBeInTheDocument();
});

test('best = lowest-cost student, worst = highest-cost', () => {
  render(<RatingSummary rows={ROWS} />);
  fireEvent.click(screen.getByRole('button', { name: 'Best' }));
  expect(screen.getByText('Ace')).toBeInTheDocument();
  expect(screen.queryByText('Slow')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('button', { name: 'Worst' }));
  expect(screen.getByText('Slow')).toBeInTheDocument();
  expect(screen.queryByText('Ace')).not.toBeInTheDocument();
});

test('filterRating limits to the chosen rating', () => {
  const rows = [...ROWS, row({ id: '5', name: 'IfrGuy', rating: 'IFR' })];
  render(<RatingSummary rows={rows} filterRating="IFR" />);
  expect(screen.getByText('IFR')).toBeInTheDocument();
  // PPL chip should not be present when filtered to IFR
  const table = screen.getByRole('table');
  expect(within(table).queryByText('PPL')).not.toBeInTheDocument();
});

test('empty state when no completed students', () => {
  render(<RatingSummary rows={[row({ id: '1', status: 'Active' })]} />);
  expect(screen.getByText('No completed students')).toBeInTheDocument();
});
