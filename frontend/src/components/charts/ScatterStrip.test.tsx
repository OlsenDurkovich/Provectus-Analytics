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

import { fireEvent } from '@testing-library/react';

test('highlighted dot uses accent color by default', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
    />,
  );
  const accentCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) => c.getAttribute('fill') === 'var(--accent)',
  );
  expect(accentCircle).toBeTruthy();
});

test('highlightInProgress swaps highlighted dot fill to warn color', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      highlightInProgress
    />,
  );
  const warnCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) => c.getAttribute('fill') === 'var(--warn)',
  );
  expect(warnCircle).toBeTruthy();
  const accentCircle = Array.from(container.querySelectorAll('circle')).find(
    (c) =>
      c.getAttribute('fill') === 'var(--accent)' &&
      c.getAttribute('r') === '7',
  );
  expect(accentCircle).toBeFalsy();
});

test('tooltip on in-progress highlighted dot suffixes "(in progress)"', () => {
  const { container } = render(
    <ScatterStrip
      points={POINTS}
      band={BAND}
      median={MEDIAN}
      highlightName="Alice"
      yLabel="Hours"
      fmt={(v) => v.toFixed(1)}
      highlightInProgress
    />,
  );
  const aliceGroup = Array.from(container.querySelectorAll('g')).find((g) =>
    Array.from(g.querySelectorAll('circle')).some(
      (c) => c.getAttribute('fill') === 'var(--warn)',
    ),
  );
  expect(aliceGroup).toBeTruthy();
  fireEvent.mouseEnter(aliceGroup!);
  const tooltipText = Array.from(container.querySelectorAll('text')).find((t) =>
    (t.textContent ?? '').includes('(in progress)'),
  );
  expect(tooltipText).toBeTruthy();
});
