import { render } from '@testing-library/react';
import { Icon } from './Icon';

test('renders an svg', () => {
  const { container } = render(<Icon name="search" size={16} />);
  expect(container.querySelector('svg')).toBeTruthy();
});

test('size prop sets width and height', () => {
  const { container } = render(<Icon name="bell" size={24} />);
  const svg = container.querySelector('svg')!;
  expect(svg.getAttribute('width')).toBe('24');
  expect(svg.getAttribute('height')).toBe('24');
});
