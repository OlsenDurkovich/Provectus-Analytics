import { render } from '@testing-library/react';
import { test, expect } from 'vitest';
import { Heatmap } from './Heatmap';
import { RatingBars } from './RatingBars';
import { RatingsList } from './RatingsList';

test('RatingBars renders SVG bars', () => {
  const { container } = render(
    <RatingBars
      data={[{ code: 'PPL', name: 'PPL', n: 10, median: 60, p25: 50, p75: 70 }]}
      metric="hours"
    />
  );
  expect(container.querySelector('svg')).toBeTruthy();
});

test('Heatmap renders 7x12 grid', () => {
  const rows = Array.from({ length: 7 }, () => Array(12).fill(0));
  const { container } = render(
    <Heatmap rows={rows} buckets={Array(12).fill('x') as string[]} />
  );
  expect(container.querySelector('.heatmap')).toBeTruthy();
});

test('RatingsList renders rating chips and bars', () => {
  const { container, getByText } = render(
    <RatingsList data={[{ rating: 'PPL', count: 5 }, { rating: 'IFR', count: 3 }]} />
  );
  expect(getByText('PPL')).toBeTruthy();
  expect(getByText('IFR')).toBeTruthy();
  expect(container.querySelectorAll('.hbar-fill').length).toBe(2);
});
