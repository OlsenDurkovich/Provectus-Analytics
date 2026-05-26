import { render } from '@testing-library/react';
import { Sparkline, Delta, Skel } from './';

test('Sparkline renders svg', () => {
  const { container } = render(<Sparkline data={[1, 2, 3]} />);
  expect(container.querySelector('svg')).toBeTruthy();
});

test('Sparkline returns null for empty data', () => {
  const { container } = render(<Sparkline data={[]} />);
  expect(container.querySelector('svg')).toBeFalsy();
});

test('Delta renders signed value with arrow', () => {
  const { container, getByText } = render(<Delta value={0.12} positive />);
  expect(getByText('0.1%')).toBeTruthy();
  expect(container.querySelector('span.delta.up')).toBeTruthy();
});

test('Delta negative carries down class', () => {
  const { container } = render(<Delta value={-1.5} positive={false} />);
  expect(container.querySelector('span.delta.down')).toBeTruthy();
});

test('Skel renders placeholder', () => {
  const { container } = render(<Skel w={80} h={20} />);
  const div = container.querySelector('.skel') as HTMLDivElement | null;
  expect(div).toBeTruthy();
  expect(div?.style.width).toBe('80px');
});
