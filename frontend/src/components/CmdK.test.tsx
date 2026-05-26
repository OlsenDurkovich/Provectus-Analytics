import { fireEvent, render, screen } from '@testing-library/react';
import { test, expect, vi } from 'vitest';
import { CmdK } from './CmdK';

function noop() {}

test('returns null when closed', () => {
  const { container } = render(
    <CmdK
      open={false}
      onClose={noop}
      onNavigate={noop}
      onSetRange={noop}
      onToggleTheme={noop}
      onImport={noop}
      onRebuild={noop}
    />,
  );
  expect(container.querySelector('.cmdk')).toBeNull();
});

test('renders nav and actions when open', () => {
  render(
    <CmdK
      open={true}
      onClose={noop}
      onNavigate={noop}
      onSetRange={noop}
      onToggleTheme={noop}
      onImport={noop}
      onRebuild={noop}
    />,
  );
  expect(screen.getByText('Go to Overview')).toBeTruthy();
  expect(screen.getByText('Toggle theme')).toBeTruthy();
  expect(screen.getByText('Rebuild database (synthetic)')).toBeTruthy();
});

test('filters by query', () => {
  render(
    <CmdK
      open={true}
      onClose={noop}
      onNavigate={noop}
      onSetRange={noop}
      onToggleTheme={noop}
      onImport={noop}
      onRebuild={noop}
    />,
  );
  fireEvent.change(screen.getByPlaceholderText('Type a command or search…'), {
    target: { value: 'rebuild' },
  });
  expect(screen.queryByText('Go to Overview')).toBeNull();
  expect(screen.getByText('Rebuild database')).toBeTruthy();
});

test('clicking item fires run + onClose', () => {
  const onClose = vi.fn();
  const onNavigate = vi.fn();
  render(
    <CmdK
      open={true}
      onClose={onClose}
      onNavigate={onNavigate}
      onSetRange={noop}
      onToggleTheme={noop}
      onImport={noop}
      onRebuild={noop}
    />,
  );
  fireEvent.click(screen.getByText('Go to Flights'));
  expect(onNavigate).toHaveBeenCalledWith('/flights');
  expect(onClose).toHaveBeenCalled();
});
