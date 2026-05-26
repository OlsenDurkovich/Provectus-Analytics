import { render } from '@testing-library/react';
import { test, expect } from 'vitest';
import { ScatterStrip } from './ScatterStrip';

const POINTS = [
  { student: 'Alice', value: 60 },
  { student: 'Bob', value: 65 },
];
const BAND = { low: 58, high: 66 };
const MEDIAN = 62;

test('renders full variant by default', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const svg = container.querySelector('svg');
  expect(svg).toBeTruthy();
  expect(svg!.getAttribute('height')).toBe('280');
});

test('mini variant renders at smaller height', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  const svg = container.querySelector('svg');
  expect(svg).toBeTruthy();
  expect(Number(svg!.getAttribute('height'))).toBeLessThan(80);
});

test('mini variant hides Y-axis label', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  const yLabel = Array.from(container.querySelectorAll('text')).find(
    (t) => t.textContent === 'Hours',
  );
  expect(yLabel).toBeUndefined();
});

test('full variant shows Y-axis label', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const yLabel = Array.from(container.querySelectorAll('text')).find(
    (t) => t.textContent === 'Hours',
  );
  expect(yLabel).toBeTruthy();
});

test('mini variant renders 2 y-axis ticks instead of 5', () => {
  const { container: fullC } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const { container: miniC } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName={null}
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      size="mini"
    />,
  );
  const fullGridLines = fullC.querySelectorAll('line[stroke="var(--grid)"]');
  const miniGridLines = miniC.querySelectorAll('line[stroke="var(--grid)"]');
  expect(fullGridLines.length).toBe(5);
  expect(miniGridLines.length).toBe(2);
});
