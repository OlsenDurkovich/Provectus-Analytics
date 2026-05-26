import { fireEvent, render, screen } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { BigKpi, DeltaText, MiniKpi, Select } from './';

test('Select renders current label and toggles options on click', () => {
  const onChange = vi.fn();
  render(
    <Select<'a' | 'b'>
      value="a"
      onChange={onChange}
      options={[{ value: 'a', label: 'Alpha' }, { value: 'b', label: 'Bravo' }]}
    />
  );
  expect(screen.getByText('Alpha')).toBeTruthy();
  fireEvent.click(screen.getByText('Alpha'));
  fireEvent.click(screen.getByText('Bravo'));
  expect(onChange).toHaveBeenCalledWith('b');
});

test('BigKpi renders label + value + optional sub', () => {
  render(<BigKpi label="Median hours" value="64.2" sub="cohort n=12" />);
  expect(screen.getByText('Median hours')).toBeTruthy();
  expect(screen.getByText('64.2')).toBeTruthy();
  expect(screen.getByText('cohort n=12')).toBeTruthy();
});

test('MiniKpi renders compactly', () => {
  render(<MiniKpi label="Hours" value="42.1" />);
  expect(screen.getByText('Hours')).toBeTruthy();
  expect(screen.getByText('42.1')).toBeTruthy();
});

test('DeltaText neutral on 0', () => {
  const { container } = render(<DeltaText value={0} />);
  expect(container.querySelector('.delta-text.neutral')).toBeTruthy();
});

test('DeltaText good when below median (better-lower)', () => {
  const { container } = render(<DeltaText value={-5} betterWhenLower fmt={(v) => `${v}h`} />);
  expect(container.querySelector('.delta-text.good')).toBeTruthy();
});

test('DeltaText bad when above median (better-lower)', () => {
  const { container } = render(<DeltaText value={5} betterWhenLower />);
  expect(container.querySelector('.delta-text.bad')).toBeTruthy();
});
