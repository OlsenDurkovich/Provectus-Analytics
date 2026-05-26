import { render } from '@testing-library/react';
import { test, expect } from 'vitest';
import { Heatmap } from './Heatmap';
import { RatingBars } from './RatingBars';
import { RatingsList } from './RatingsList';
import { ScatterStrip } from './ScatterStrip';

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

test('ScatterStrip renders an SVG with dots for each point', () => {
  const points = [
    { student: 'Alice', value: 60 },
    { student: 'Bob', value: 70 },
    { student: 'Carol', value: 55 },
  ];
  const { container } = render(
    <ScatterStrip
      points={points}
      band={{ low: 58, high: 72 }}
      median={65}
      highlightNames={["Bob"]}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  expect(container.querySelector('svg')).toBeTruthy();
  // 3 dots rendered as circles
  expect(container.querySelectorAll('circle').length).toBe(3);
});

test('ScatterStrip renders without highlighted point', () => {
  const { container } = render(
    <ScatterStrip
      points={[{ student: 'Alice', value: 60 }]}
      band={{ low: 55, high: 65 }}
      median={60}
      highlightNames={[]}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  expect(container.querySelector('svg')).toBeTruthy();
});
