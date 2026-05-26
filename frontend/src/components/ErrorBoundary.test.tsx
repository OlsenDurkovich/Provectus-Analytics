import { render, screen } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { ErrorBoundary } from './ErrorBoundary';

function Bomb(): JSX.Element {
  throw new Error('boom-from-test');
}

test('renders children when no error', () => {
  render(
    <ErrorBoundary>
      <div>safe-child</div>
    </ErrorBoundary>,
  );
  expect(screen.getByText('safe-child')).toBeTruthy();
});

test('catches and shows fallback UI', () => {
  const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  render(
    <ErrorBoundary>
      <Bomb />
    </ErrorBoundary>,
  );
  expect(screen.getByText('Something broke')).toBeTruthy();
  expect(screen.getByText('boom-from-test')).toBeTruthy();
  errorSpy.mockRestore();
});
